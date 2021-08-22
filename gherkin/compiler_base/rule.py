from abc import ABC
from typing import Union

from gherkin.compiler_base.exception import SequenceEnded, RuleNotFulfilled, SequenceNotFinished, GrammarNotUsed
from gherkin.compiler_base.grammar import Grammar
from gherkin.compiler_base.mixin import SequenceToObjectMixin, IndentMixin
from gherkin.compiler_base.terminal import TerminalSymbol
from gherkin.compiler_base.wrapper import TokenWrapper


class Rule(IndentMixin, SequenceToObjectMixin, ABC):
    supports_list_as_children = False

    def __init__(self, child_rule):
        super().__init__()
        self.child_rule = child_rule

        if isinstance(child_rule, list) and not self.supports_list_as_children:
            raise ValueError('A {} does not support a list of objects as a child'.format(self.__class__.__name__))

        # validate the given child
        if isinstance(child_rule, list):
            for c in child_rule:
                self._validate_init_child(c)
        else:
            self._validate_init_child(child_rule)

    def get_next_valid_tokens(self):
        raise NotImplementedError()

    def _validate_init_child(self, child):
        """Validation on __init__"""
        if not isinstance(child, Rule) and not isinstance(child, TerminalSymbol) and not isinstance(child, Grammar):
            raise ValueError('You cannot use other children than Rule objects or RuleObjects around your own objects.')

    def _validate_sequence(self, sequence, index) -> int:
        """
        Implemented by each rule. Does the validation of a given sequence. Can be called recursively.
        The index represents the current index at which the sequence is checked.
        """
        raise NotImplementedError()

    def _build_error_message(self, keywords, token_wrapper=None, message=''):
        """Builds the message for RuleNotFulfilled and SequenceEnded exceptions."""
        if len(keywords) == 1:
            message += 'Expected {}.'.format(keywords[0])
        elif len(keywords) > 1:
            message += 'Expected one of: {}.'.format(', '.join(['"{}"'.format(k) for k in keywords]))

        if token_wrapper:
            if not keywords:
                message += '{} is invalid. {}'.format(token_wrapper.get_text(), token_wrapper.get_place_to_search())
            else:
                message += ' Got {} instead. {}'.format(token_wrapper.get_text(), token_wrapper.get_place_to_search())

        return message

    def _validate_token_wrapper(self, sequence: [TokenWrapper], terminal_symbol: TerminalSymbol, index: int):
        """
        Validates if a given rule token belongs to a rule class.

        :raises SequenceEnded: if the sequence ends abruptly this error is risen
        :raises RuleNotFulfilled: if the token_wrapper in the sequence does not match the terminal_symbol
        """
        keywords = terminal_symbol.get_keywords()
        suggested_tokens = terminal_symbol.get_next_valid_tokens()

        try:
            token_wrapper = sequence[index]
        except IndexError:
            message = self._build_error_message(keywords, message='Input ended abruptely. ')
            raise SequenceEnded(
                message,
                terminal_symbol=terminal_symbol,
                sequence_index=index,
                rule=self,
                suggested_tokens=suggested_tokens,
            )

        assert isinstance(token_wrapper, TokenWrapper)
        assert isinstance(terminal_symbol, TerminalSymbol)

        if not terminal_symbol.token_wrapper_is_valid(token_wrapper):
            message = self._build_error_message(keywords, token_wrapper)

            raise RuleNotFulfilled(
                message,
                terminal_symbol=terminal_symbol,
                sequence_index=index,
                rule=self,
                suggested_tokens=suggested_tokens,
            )

        self.on_token_wrapper_valid(token_wrapper)

    def on_token_wrapper_valid(self, token_wrapper: TokenWrapper):
        token_wrapper.token.set_grammar_meta_value('suggested_indent_level', self.get_suggested_indent_level())

    def _get_valid_index_for_child(
            self,
            child: Union['Rule', 'TerminalSymbol', 'Grammar'],
            sequence: ['TokenWrapper'],
            index: int,
    ) -> int:
        """
        This function is used in the validation. It will return the next valid index in the sequence for the
        current rule (this instance) for a given child.

        :raises RuleNotFulfilled (see _validate_token_wrapper)
        :raises SequenceEnded (see _validate_token_wrapper)

        :param child: a child of a rule - can be a Rule or a RuleClass
        :param sequence: the sequence that is validated
        :param index: the index in the sequence right now
        :return:
        """
        # if a Rule is given, let is handle the sequence instead
        if isinstance(child, Rule):
            return child._validate_sequence(sequence, index)

        if isinstance(child, Grammar):
            # noinspection PyProtectedMember
            return child._validate_sequence(sequence, index)

        # if a RuleClass is given, validate the rule token against that class
        if isinstance(child, TerminalSymbol):
            self._validate_token_wrapper(sequence, child, index)

            # if it is valid, go to the next token in the sequence
            return index + 1

        raise ValueError('This should not happen.')

    def convert(self, sequence):
        """
        Can be called to convert a given sequence to an object. The returned object depends on the Rule.
        """
        self.validate_sequence(sequence)
        return self.sequence_to_object(sequence)

    def validate_sequence(self, sequence: ['TokenWrapper'], index=0):
        """
        Public function to validate a given sequence. May raise a RuleNotFulfilled or a SequenceNotFinished.
        """
        assert all([isinstance(el, TokenWrapper) for el in sequence]), 'Every entry in the passed sequence must be of ' \
                                                                       'class "RuleToken"'

        try:
            result_index = self._validate_sequence(sequence, index)
        except SequenceEnded as e:
            raise RuleNotFulfilled(
                str(e),
                sequence_index=e.sequence_index,
                terminal_symbol=e.terminal_symbol,
                rule=e.rule,
                suggested_tokens=e.suggested_tokens,
            )

        if result_index < len(sequence):
            raise SequenceNotFinished()

        return result_index

    def __str__(self):
        return 'Rule {} - {}'.format(self.__class__.__name__, self.child_rule)


class Optional(Rule):
    """
    Can be used to mark something a token as optional.
    """
    def __init__(self, child, important=False):
        super().__init__(child)
        self.important = important

        self.child_rule.set_parent(self)

    def get_next_valid_tokens(self):
        if not self.important:
            return []

        tokens = self.child_rule.get_next_valid_tokens()
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
            return self._get_valid_index_for_child(self.child_rule, sequence, index)
        except (RuleNotFulfilled, GrammarNotUsed, SequenceEnded):
            # if not valid, continue at current index
            return index

    def sequence_to_object(self, sequence, index=0):
        """
        Transforms an entry of a sequence at an index into an object. This will either return:
            -> None if the requirement of the child is not met
            -> a RuleToken if the child is a RuleAlias
            -> Whatever the child has defined if the child is a Grammar or a Rule
        """
        self._validate_sequence(sequence, index)

        # check if the child exists - if not return None
        try:
            self._get_valid_index_for_child(self.child_rule, sequence, index)
        except (RuleNotFulfilled, GrammarNotUsed, SequenceEnded):
            return None

        return self.child_rule.sequence_to_object(sequence, index)


class OneOf(Rule):
    """
    Can be used as an OR operation: Any token that is passed is valid. If none exists, an error is thrown.
    """
    supports_list_as_children = True

    def __init__(self, child):
        super().__init__(child)

        if not isinstance(child, list):
            raise ValueError('You must use a list for OneOf')

        for child in self.child_rule:
            child.set_parent(self)

    def get_next_valid_tokens(self):
        output = []

        for child in self.child_rule:
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

        for child in self.child_rule:
            try:
                self._get_valid_index_for_child(child, sequence, index)
            except (RuleNotFulfilled, SequenceEnded, GrammarNotUsed):
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
        for child in self.child_rule:
            try:
                return self._get_valid_index_for_child(child, sequence, index)
            except (RuleNotFulfilled, GrammarNotUsed, SequenceEnded) as e:
                errors.append((e, child))

        # if each child has thrown an error, this is invalid
        suggested_tokens = [e.suggested_tokens for e, token in errors]
        raise RuleNotFulfilled(
            str(errors[0][0]),
            sequence_index=index,
            terminal_symbol=errors[0][1],
            rule=self,
            # flatten the list
            suggested_tokens=[item for sublist in suggested_tokens for item in sublist],
        )


class Repeatable(Rule):
    """Allows any amount of repetition of the passed child. If it is optional, minimum=0 can be passed."""

    def __init__(self, child, minimum=1, important=False):
        super().__init__(child)
        self.minimum = minimum
        self.important = important

        self.child_rule.set_parent(self)

    def get_next_valid_tokens(self):
        if self.minimum == 0 and not self.important:
            return []

        tokens = self.child_rule.get_next_valid_tokens()
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
                index = self._get_valid_index_for_child(self.child_rule, sequence, index)
            except (RuleNotFulfilled, GrammarNotUsed, SequenceEnded) as e:
                if isinstance(e, GrammarNotUsed):
                    break_error = RuleNotFulfilled(
                        str(e),
                        sequence_index=index,
                        terminal_symbol=e.terminal_symbol,
                        rule=e.rule,
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
                next_round_index = self._get_valid_index_for_child(self.child_rule, sequence, index)
                output.append(self.child_rule.sequence_to_object(sequence, index))
                index = next_round_index
            except (RuleNotFulfilled, GrammarNotUsed, SequenceEnded):
                break
        return output


class Chain(Rule):
    """
    Allows a specific order of tokens to be checked. If the exact order is not correct, an error is thrown.
    """
    supports_list_as_children = True

    def __init__(self, child):
        super().__init__(child)

        if not isinstance(child, list):
            raise ValueError('You must use a list for a Chain')

        for child in self.child_rule:
            child.set_parent(self)

    def get_next_valid_tokens(self):
        if len(self.child_rule) == 0:
            return []

        output = []
        for child_rule in self.child_rule:
            valid_tokens = child_rule.get_next_valid_tokens()

            if valid_tokens:
                if not isinstance(valid_tokens, list):
                    valid_tokens = [valid_tokens]

                output += valid_tokens

            if not isinstance(child_rule, (Optional, Repeatable)):
                break

        return output

    def sequence_to_object(self, sequence, index=0):
        """
        Returns a list of objects that represent an area at a starting index of a given sequence. The list will
        contain entries where each entry of the list is determined by the child.
            -> If a child is a rule, look at its implementation of `sequence_to_object`
            -> If a child is a grammar, look at its implementation of `sequence_to_object`
            -> If a child is RuleAlias, the entry will be the current RuleToken at the given index
        """
        output = []
        self._validate_sequence(sequence, index)

        for child in self.child_rule:
            # get the index where we will end
            try:
                next_round_index = self._get_valid_index_for_child(child, sequence, index)
            except (GrammarNotUsed, RuleNotFulfilled):
                continue

            output.append(child.sequence_to_object(sequence, index))
            index = next_round_index

        return output

    def _validate_sequence(self, sequence, index):
        # validate each child and get the index
        for child in self.child_rule:
            try:
                index = self._get_valid_index_for_child(child, sequence, index)
            except GrammarNotUsed as e:
                raise RuleNotFulfilled(
                    str(e),
                    terminal_symbol=e.terminal_symbol,
                    sequence_index=e.sequence_index,
                    rule=e.rule,
                    suggested_tokens=e.suggested_tokens,
                )

        return index


class IndentBlock(Rule):
    supports_list_as_children = True

    def __init__(self, child):
        if isinstance(child, list):
            child = Chain(child)

        super().__init__(child)
        self.child_rule.set_parent(self)

    def get_suggested_indent_level(self):
        level = super().get_suggested_indent_level()

        return level + 1

    def _validate_sequence(self, sequence, index):
        return self.child_rule._validate_sequence(sequence, index)

    def sequence_to_object(self, sequence, index=0):
        return self.child_rule.sequence_to_object(sequence, index)

    def get_next_valid_tokens(self):
        return self.child_rule.get_next_valid_tokens()
