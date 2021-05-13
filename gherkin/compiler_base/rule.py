from typing import Union

from gherkin.compiler_base.exception import SequenceEnded, RuleNotFulfilled, SequenceNotFinished, GrammarNotUsed
from gherkin.compiler_base.grammar import Grammar
from gherkin.compiler_base.wrapper import RuleAlias, RuleToken


class Rule(object):
    supports_list_as_children = False

    def __init__(self, child_rule, debug=False):
        self.child_rule = child_rule
        self.debug = debug

        if isinstance(child_rule, list) and not self.supports_list_as_children:
            raise ValueError('A {} does not support a list of objects as a child'.format(self.__class__.__name__))

        # validate the given child
        if isinstance(child_rule, list):
            for c in child_rule:
                self._validate_init_child(c)
        else:
            self._validate_init_child(child_rule)

    def _validate_init_child(self, child):
        """Validation on __init__"""
        if not isinstance(child, Rule) and not isinstance(child, RuleAlias) and not isinstance(child, Grammar):
            raise ValueError('You cannot use other children than Rule objects or RuleObjects around your own objects.')

    def _validate_sequence(self, sequence, index) -> int:
        """
        Implemented by each rule. Does the validation of a given sequence. Can be called recursively.
        The index represents the current index at which the sequence is checked.
        """
        raise NotImplementedError()

    def _build_error_message(self, keywords, rule_token=None, message=''):
        """Builds the message for RuleNotFulfilled and SequenceEnded exceptions."""
        if len(keywords) == 1:
            message += 'Expected {}.'.format(keywords[0])
        elif len(keywords) > 1:
            message += 'Expected one of: {}.'.format(', '.join(['"{}"'.format(k) for k in keywords]))

        if rule_token:
            if not keywords:
                message += '{} is invalid. {}'.format(rule_token.get_text(), rule_token.get_place_to_search())
            else:
                message += ' Got {} instead. {}'.format(rule_token.get_text(), rule_token.get_place_to_search())

        return message

    def _validate_rule_token(self, sequence: RuleToken, rule_alias: RuleAlias, index: int):
        """
        Validates if a given rule token belongs to a rule class.

        :raises SequenceEnded: if the sequence ends abruptly this error is risen
        :raises RuleNotFulfilled: if the rule_token in the sequence does not match the rule_alias
        """
        keywords = rule_alias.get_keywords()

        try:
            rule_token = sequence[index]
        except IndexError:
            message = self._build_error_message(keywords, message='Input ended abruptely. ')
            raise SequenceEnded(message, rule_alias=rule_alias, sequence_index=index, rule=self)

        assert isinstance(rule_token, RuleToken)
        assert isinstance(rule_alias, RuleAlias)

        if not rule_alias.rule_token_is_valid(rule_token):
            message = self._build_error_message(keywords, rule_token)

            raise RuleNotFulfilled(message, rule_alias=rule_alias, sequence_index=index, rule=self)

    def _get_valid_index_for_child(self, child: Union['Rule', 'RuleAlias', 'Grammar'], sequence: ['RuleToken'], index: int) -> int:
        """
        This function is used in the validation. It will return the next valid index in the sequence for the
        current rule (this instance) for a given child.

        :raises RuleNotFulfilled (see _validate_rule_token)
        :raises SequenceEnded (see _validate_rule_token)

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
        if isinstance(child, RuleAlias):
            self._validate_rule_token(sequence, child, index)

            # if it is valid, go to the next token in the sequence
            return index + 1

        raise ValueError('This should not happen.')

    def sequence_to_object(self, sequence, index=0):
        """
        Defines how a sequence at a given index is transformed into an object.

        This function may return a RuleToken, None, [RuleToken] or a custom object.
        """
        raise NotImplementedError()

    def convert(self, sequence):
        """
        Can be called to convert a given sequence to an object. The returned object depends on the Rule.
        """
        self.validate_sequence(sequence)
        return self.sequence_to_object(sequence)

    def validate_sequence(self, sequence: ['RuleToken'], index=0):
        """
        Public function to validate a given sequence. May raise a RuleNotFulfilled or a SequenceNotFinished.
        """
        assert all([isinstance(el, RuleToken) for el in sequence]), 'Every entry in the passed sequence must be of ' \
                                                                    'class "RuleToken"'

        try:
            result_index = self._validate_sequence(sequence, index)
        except SequenceEnded as e:
            raise RuleNotFulfilled(str(e), sequence_index=e.sequence_index, rule_alias=e.rule_alias, rule=e.rule)

        if result_index < len(sequence):
            raise SequenceNotFinished()

        return result_index

    def __str__(self):
        return 'Rule {} - {}'.format(self.__class__.__name__, self.child_rule)


class Optional(Rule):
    """
    Can be used to mark something a token as optional.
    """
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

        # if the child is a grammar, let it resolve
        if isinstance(self.child_rule, Grammar):
            return self.child_rule.sequence_to_object(sequence, index)

        # if the child is a Rule, let it resolve
        if isinstance(self.child_rule, Rule):
            return self.child_rule.sequence_to_object(sequence, index)

        # else it returns the RuleToken that was found
        return sequence[index]


class OneOf(Rule):
    """
    Can be used as an OR operation: Any token that is passed is valid. If none exists, an error is thrown.
    """
    supports_list_as_children = True

    def __init__(self, child):
        super().__init__(child)

        if not isinstance(child, list):
            raise ValueError('You must use a list for OneOf')

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

            if isinstance(child, Rule):
                return child.sequence_to_object(sequence, index)

            if isinstance(child, Grammar):
                return child.sequence_to_object(sequence, index)

            return sequence[index]

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
        raise RuleNotFulfilled(str(errors[0][0]), sequence_index=index, rule_alias=errors[0][1], rule=self)


class Repeatable(Rule):
    """Allows any amount of repetition of the passed child. If it is optional, minimum=0 can be passed."""

    def __init__(self, child, minimum=1, debug=False):
        super().__init__(child, debug)
        self.minimum = minimum

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
                    break_error = RuleNotFulfilled(str(e), sequence_index=index, rule_alias=e.rule_alias, rule=e.rule)
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

                if isinstance(self.child_rule, Grammar):
                    # noinspection PyProtectedMember
                    output.append(self.child_rule.sequence_to_object(sequence, index))
                    index = next_round_index
                    continue

                if isinstance(self.child_rule, Rule):
                    output.append(self.child_rule.sequence_to_object(sequence, index))
                    index = next_round_index
                    continue

                output += sequence[index:next_round_index]
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

            if isinstance(child, Grammar):
                output.append(child.sequence_to_object(sequence, index))
                index = next_round_index
                continue

            if isinstance(child, Rule):
                to_add = child.sequence_to_object(sequence, index)
                index = next_round_index
                output.append(to_add)
                continue

            output.append(sequence[index])
            index = next_round_index

        return output

    def _validate_sequence(self, sequence, index):
        # validate each child and get the index
        for child in self.child_rule:
            try:
                index = self._get_valid_index_for_child(child, sequence, index)
            except GrammarNotUsed as e:
                raise RuleNotFulfilled(str(e), rule_alias=e.rule_alias, sequence_index=e.sequence_index, rule=e.rule)

        return index
