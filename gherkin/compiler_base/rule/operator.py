from abc import ABC

from gherkin.compiler_base.exception import SequenceEnded, RuleNotFulfilled, NonTerminalNotUsed
from gherkin.compiler_base.mixin import IndentMixin
from gherkin.compiler_base.recursive import RecursiveValidationBase


class RuleOperator(IndentMixin, RecursiveValidationBase, ABC):
    """
    This is a base class for all operations that can be used inside of rules.
    """
    supports_list_as_children = False

    def __init__(self, child):
        super().__init__()

        if isinstance(child, list) and not self.supports_list_as_children:
            raise ValueError('A {} does not support a list of objects as a child'.format(self.__class__.__name__))

        # validate the given child
        if isinstance(child, list):
            self.children = child
            for c in child:
                self._validate_init_child(c)
        else:
            self.child = child
            self._validate_init_child(child)

    def get_next_valid_tokens(self):
        """
        Returns all tokens that can be valid (basically like follow). This is mainly used when there is an error
        to returns suggestions which Token should come next.
        """
        raise NotImplementedError()

    def _validate_init_child(self, child):
        """Validation on __init__"""
        if not isinstance(child, RecursiveValidationBase):
            raise ValueError('You cannot use other children than Rule objects or RuleObjects around your own objects.')

    def get_next_pointer_index(self, child, sequence, current_index) -> int:
        """
        An operator always lets the child handle which pointer index comes next.
        """
        # noinspection PyProtectedMember
        return child._validate_sequence(sequence, current_index)

    def __str__(self):
        return 'Rule {} - {}'.format(self.__class__.__name__, self.child)


class Optional(RuleOperator):
    """
    Can be used to mark something as optional.
    """
    def __init__(self, child, show_in_autocomplete=False):
        super().__init__(child)
        self.show_in_autocomplete = show_in_autocomplete

        self.child.set_parent(self)

    def to_ebnf(self, ebnf_entries=None):
        """
        Optional is represented as `[<value>]`
        """
        return '[{}]'.format(self.child.to_ebnf(ebnf_entries))

    def get_next_valid_tokens(self):
        if not self.show_in_autocomplete:
            return []

        tokens = self.child.get_next_valid_tokens()
        if not isinstance(tokens, list):
            tokens = [tokens]
        return tokens

    def _validate_init_child(self, child):
        super()._validate_init_child(child)

        if isinstance(child, Repeatable):
            raise ValueError('Do not use Repeatable as a child of Optional. Use Repeatable(minimum=0) instead.')

    def _validate_sequence(self, sequence, index) -> int:
        # try to get the next index. If that fails, just ignore, since it is optional
        try:
            return self.get_next_pointer_index(self.child, sequence, index)
        except (RuleNotFulfilled, NonTerminalNotUsed, SequenceEnded):
            # if not valid, continue at current index
            return index

    def sequence_to_object(self, sequence, index=0):
        """
        Transforms an entry of a sequence at an index into an object. This will either return:
            -> None if the requirement of the child is not met
            -> a Token if the child is a `TerminalSymbol`
            -> Whatever the child has defined if the child is a NonTerminal or RuleOperator
        """
        self._validate_sequence(sequence, index)

        # check if the child exists - if not return None
        try:
            self.get_next_pointer_index(self.child, sequence, index)
        except (RuleNotFulfilled, NonTerminalNotUsed, SequenceEnded):
            return None

        return self.child.sequence_to_object(sequence, index)


class OneOf(RuleOperator):
    """
    Can be used as an OR operation: Any token that is passed is valid. If none exists, an error is thrown.
    """
    supports_list_as_children = True

    def __init__(self, child):
        super().__init__(child)

        if not isinstance(child, list):
            raise ValueError('You must use a list for OneOf')

        for child in self.children:
            child.set_parent(self)

    def to_ebnf(self, ebnf_entries=None):
        """
        OneOf is represented as (a | b | c)
        """
        return ' | '.join('({})'.format(child.to_ebnf(ebnf_entries)) for child in self.children)

    def get_next_valid_tokens(self):
        output = []

        for child in self.children:
            tokens = child.get_next_valid_tokens()
            if not tokens:
                continue

            if not isinstance(tokens, list):
                tokens = [tokens]
            output += tokens

        return output

    def sequence_to_object(self, sequence, index=0):
        """
        Returns an object for an entry in a sequence at a given index. This will return:
            -> the first child that is valid will return its value
                -> RuleAlias: the current RuleToken
                -> Grammar or Rule: get its value instead.
        """
        self._validate_sequence(sequence, index)

        for child in self.children:
            try:
                self.get_next_pointer_index(child, sequence, index)
            except (RuleNotFulfilled, SequenceEnded, NonTerminalNotUsed):
                continue

            return child.sequence_to_object(sequence, index)

        assert False, 'This should not happen because it was validated beforehand - there should be one valid entry.'

    def _validate_init_child(self, child):
        super()._validate_init_child(child)

        if isinstance(child, Optional):
            raise ValueError('You should not use Optional as a Child of OneOf.')

        if isinstance(child, Repeatable) and child.minimum == 0:
            raise ValueError('You should not use minimum=0 on Repeatable while using OneOf as a parent.')

    def _validate_sequence(self, sequence, index):
        errors = []

        # go through each child and validate it for the child; collect all errors
        for child in self.children:
            try:
                return self.get_next_pointer_index(child, sequence, index)
            except (RuleNotFulfilled, NonTerminalNotUsed, SequenceEnded) as e:
                errors.append((e, child))

        # if each child has thrown an error, this is invalid
        suggested_tokens = [e.suggested_tokens for e, token in errors]
        raise RuleNotFulfilled(
            str(errors[0][0]),
            sequence_index=index,
            terminal_symbol=errors[0][1],
            comes_from=self,
            # flatten the list
            suggested_tokens=[item for sublist in suggested_tokens for item in sublist],
        )


class Repeatable(RuleOperator):
    """Allows any amount of repetition of the passed child. If it is optional, minimum=0 can be passed."""

    def __init__(self, child, minimum=1, show_in_autocomplete=False):
        super().__init__(child)
        self.minimum = minimum
        self.show_in_autocomplete = show_in_autocomplete

        self.child.set_parent(self)

    def to_ebnf(self, ebnf_entries=None):
        """
        Repeatable is represented as `{<value>}` for minimum=0, `<value>, {<value>}` for minimum=1 and so on.
        """
        base_string = ''
        child_ebnf = self.child.to_ebnf(ebnf_entries)

        if self.minimum > 0:
            for _ in range(self.minimum):
                base_string += '{}, '.format(child_ebnf)

        return '{}{}{}{}'.format(base_string, '{', child_ebnf, '}')

    def get_next_valid_tokens(self):
        if self.minimum == 0 and not self.show_in_autocomplete:
            return []

        tokens = self.child.get_next_valid_tokens()
        if not isinstance(tokens, list):
            tokens = [tokens]

        return tokens

    def _validate_init_child(self, child):
        super()._validate_init_child(child)

        if isinstance(child, Optional):
            raise ValueError('You must not use Optional as a child of Repeatable. Use minimum=0 instead.')

    def _validate_sequence(self, sequence, index):
        rounds_done = 0

        # try to validate the children as long as there are no errors
        while True:
            try:
                index = self.get_next_pointer_index(self.child, sequence, index)
            except (RuleNotFulfilled, NonTerminalNotUsed, SequenceEnded) as e:
                if isinstance(e, NonTerminalNotUsed):
                    break_error = RuleNotFulfilled(
                        str(e),
                        sequence_index=index,
                        terminal_symbol=e.terminal_symbol,
                        comes_from=e.comes_from,
                        suggested_tokens=e.suggested_tokens,
                    )
                else:
                    break_error = e
                break
            else:
                rounds_done += 1

        # check if the minimum numbers of rounds were done
        if break_error and rounds_done < self.minimum:
            raise break_error

        return index

    def sequence_to_object(self, sequence, index=0):
        """
        Returns a list of entries for a given sequence at a special index. This will return a list of whatever
        the child will return. If no valid entry was found it will simply return an empty list.
        """
        output = []
        self._validate_sequence(sequence, index)

        while True:
            try:
                next_round_index = self.get_next_pointer_index(self.child, sequence, index)
                output.append(self.child.sequence_to_object(sequence, index))
                index = next_round_index
            except (RuleNotFulfilled, NonTerminalNotUsed, SequenceEnded):
                break
        return output


class Chain(RuleOperator):
    """
    Allows a specific order of tokens to be checked. If the exact order is not correct, an error is thrown.
    """
    supports_list_as_children = True

    def __init__(self, child):
        super().__init__(child)

        if not isinstance(child, list):
            raise ValueError('You must use a list for a Chain')

        for child in self.children:
            child.set_parent(self)

    def to_ebnf(self, ebnf_entries=None):
        """
        Chain is represented as `<value_1>, <value_2>`
        """
        return ', '.join(child.to_ebnf(ebnf_entries) for child in self.children)

    def get_next_valid_tokens(self):
        if len(self.children) == 0:
            return []

        output = []
        for child in self.children:
            valid_tokens = child.get_next_valid_tokens()

            if valid_tokens:
                if not isinstance(valid_tokens, list):
                    valid_tokens = [valid_tokens]

                output += valid_tokens

            if not isinstance(child, (Optional, Repeatable)):
                break

        return output

    def sequence_to_object(self, sequence, index=0):
        """
        Returns a list of objects that represent an area at a starting index of a given sequence. The list will
        contain entries where each entry of the list is determined by the child.
        """
        output = []
        self._validate_sequence(sequence, index)

        for child in self.children:
            # get the index where we will end
            try:
                next_round_index = self.get_next_pointer_index(child, sequence, index)
            except (NonTerminalNotUsed, RuleNotFulfilled):
                continue

            output.append(child.sequence_to_object(sequence, index))
            index = next_round_index

        return output

    def _validate_sequence(self, sequence, index):
        # validate each child and get the index
        for child in self.children:
            try:
                index = self.get_next_pointer_index(child, sequence, index)
            except NonTerminalNotUsed as e:
                raise RuleNotFulfilled(
                    str(e),
                    terminal_symbol=e.terminal_symbol,
                    sequence_index=e.sequence_index,
                    comes_from=e.comes_from,
                    suggested_tokens=e.suggested_tokens,
                )

        return index

