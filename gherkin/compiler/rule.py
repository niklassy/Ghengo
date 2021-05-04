from typing import Union, Iterable
from gherkin.compiler.token import Rule as _Rule


class RuleNotFulfilled(Exception):
    def __init__(self, msg, rule_alias, sequence_index):
        super().__init__(msg)
        self.rule_alias = rule_alias
        self.sequence_index = sequence_index


class GrammarInvalid(Exception):
    pass


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

    def _validate_rule_token(self, rule_token: 'RuleToken', rule_alias: 'RuleAlias', index: int):
        """
        Validates if a given rule token belongs to a rule class. If not a RuleNotFulfilled is risen.
        """
        assert isinstance(rule_token, RuleToken)
        assert isinstance(rule_alias, RuleAlias)

        if not rule_alias.rule_token_is_valid(rule_token):
            keywords = rule_alias.get_keywords()

            if len(keywords) == 1:
                message = 'Expected "{}". Got "{}" instead. {}.'.format(
                    keywords[0], rule_token.get_text(), rule_token.get_place_to_search())
            elif len(keywords) == 0:
                message = '{} is invalid. {}'.format(rule_token.get_text(), rule_token.get_place_to_search())
            else:
                message = 'Expected one of {}. Got "{}" instead. {}.'.format(
                    ', '.join(['"{}"'.format(k) for k in keywords]), rule_token.get_text(),
                    rule_token.get_place_to_search()
                )

            raise RuleNotFulfilled(message, rule_alias=rule_alias, sequence_index=index)

    def _get_valid_index_for_child(self, child: Union['Rule', 'RuleAlias'], sequence: ['RuleToken'], index: int) -> int:
        """
        This function is used in the validation. It will return the next valid index in the sequence for the
        current rule (this instance) for a given child.

        :raises RuleNotFulfilled

        :param child: a child of a rule - can be a Rule or a RuleClass
        :param sequence: the sequence that is validated
        :param index: the index in the sequence right now
        :return:
        """
        rule_token: 'RuleToken' = sequence[index]

        # if a Rule is given, let is handle the sequence instead
        if isinstance(child, Rule):
            return child._validate_sequence(sequence, index)

        if isinstance(child, Grammar):
            return child.validate_sequence(sequence, index)

        # if a RuleClass is given, validate the rule token against that class
        if isinstance(child, RuleAlias):
            self._validate_rule_token(rule_token, child, index)

            # if it is valid, go to the next token in the sequence
            return index + 1

        raise ValueError('This should not happen.')

    def validate_sequence(self, sequence: ['RuleToken']):
        """
        Public function to validate a given sequence. May raise a RuleNotFulfilled
        """
        assert all([isinstance(el, RuleToken) for el in sequence]), 'Every entry in the passed sequence must be of ' \
                                                                    'class "RuleToken"'

        self._validate_sequence(sequence, 0)

    def __str__(self):
        return 'Rule {} - {}'.format(self.__class__.__name__, self.child_rule)


class Optional(Rule):
    """
    Can be used to mark something a token as optional.
    """
    def _validate_init_child(self, child):
        super()._validate_init_child(child)

        if isinstance(child, Grammar):
            raise ValueError('Dont use Optional to indicate that a grammar is optional. Use the optional kwarg on'
                             ' the grammar instead.')

    def _validate_sequence(self, sequence, index) -> int:
        # try to get the next index. If that fails, just ignore, since it is optional
        try:
            return self._get_valid_index_for_child(self.child_rule, sequence, index)
        except RuleNotFulfilled:
            # if not valid, continue at current index
            return index


class OneOf(Rule):
    """
    Can be used as an OR operation: Any token that is passed is valid. If none exists, an error is thrown.
    """
    supports_list_as_children = True

    def __init__(self, child):
        super().__init__(child)
        assert isinstance(child, list), 'You must use a list for OneOf'

    def _validate_sequence(self, sequence, index):
        errors = []

        # go through each child and validate it for the child; collect all errors
        for child in self.child_rule:
            try:
                index = self._get_valid_index_for_child(child, sequence, index)
                break
            except RuleNotFulfilled as e:
                errors.append(e)

        # if each child has thrown an error, this is invalid
        if len(errors) == len(self.child_rule):
            raise errors[0]

        return index


class Repeatable(Rule):
    """Allows any amount of repetition of the passed child. If it is optional, minimum=0 can be passed."""

    def __init__(self, child, minimum=1, debug=False):
        super().__init__(child, debug)
        self.minimum = minimum

        assert not isinstance(child, list), 'You must not use a list as a child of Repeatable, use Chain ' \
                                            'or OneOf instead.'
        assert not isinstance(child, Optional), 'You must not use Optional as a child of ' \
                                                'Repeatable. Use minimum=0 instead.'

    def _validate_sequence(self, sequence, index):
        rounds_done = 0

        # try to validate the children as long as there are no errors
        while True:
            try:
                index = self._get_valid_index_for_child(self.child_rule, sequence, index)
            except (RuleNotFulfilled, GrammarInvalid) as e:
                break_error = e
                break
            else:
                rounds_done += 1

        # check if the minimum numbers of rounds were done
        if break_error and rounds_done < self.minimum:
            raise break_error

        return index


class Chain(Rule):
    """
    Allows a specific order of tokens to be checked. If the exact order is not correct, an error is thrown.
    """
    supports_list_as_children = True

    def _validate_sequence(self, sequence, index):
        # validate each child and get the index
        for child in self.child_rule:
            index = self._get_valid_index_for_child(child, sequence, index)

        return index


class RuleAlias(object):
    """
    This is a wrapper for defining rules. It is a wrapper around any custom class that is used while defining
    rules. For this project, the class could be removed, but it is a nice wrapper for future usage.
    """
    def __init__(self, token_cls):
        self.token_cls = token_cls

    def rule_token_is_valid(self, rule_token: 'RuleToken') -> bool:
        """
        Check if a given rule_token belongs to the class that this wrapper represents. Used by rules to check if a
        value is valid for this class.
        """
        return isinstance(rule_token.token, self.token_cls)

    def get_keywords(self) -> [str]:
        """
        Return a list of keywords. Used by rules to see what keywords are expected. So: what is expected to be found
        for this class? How can this token be represented as a string?
        """
        return self.token_cls.get_keywords()

    def __str__(self):
        return str(self.token_cls)

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return self.token_cls == other.token_cls


class RuleToken(object):
    """
    This is a wrapper around any custom token object. It is used to allow rules to get the line_number and the
    text of a token. For this project, the class could be removed, but it is a nice wrapper for future usage.
    """
    def __init__(self, token):
        self.token = token
        self.rule_alias = RuleAlias(token.__class__)

    def get_place_to_search(self) -> str:
        """Is used by rules to add information where a token can be found."""
        return 'Near line: {}'.format(self.token.line.line_index)

    def get_text(self) -> str:
        """Defines how to represent a token in text. It is used by rules to display what the current value is."""
        return self.token.matched_keyword_full

    def __str__(self):
        return str(self.token)


class Grammar(object):
    """
    A grammar represents a combination of rules that has a special criterion to recognize it with.
    This criterion is a RuleAlias. If there is an error while validating a grammar object,
    it will check:
        - am i optional? - if yes, continue normally

        - did the error occur AFTER the defined RuleAlias was validated?
            -> if yes, it means that the input `tries` to create this Grammar
        - was the error raised by that exact RuleAlias?
            -> if yes, it means again that the input `tried` to create this Grammar

        => if either of those cases are true, this will raise a GrammarInvalid exception.

    This is useful to differentiate between:
        - is the grammar optional?
        - did the input actually try to create this Grammar?
        - should the validation continue?

    Grammar objects seperate Rules from each other and isolate each "Area" of grammar. If
    a rule raises an error, the grammar catches and handles it.
    """
    name = None
    rule = None
    criterion_rule_alias: RuleAlias = None

    def __init__(self, optional=False):
        self.optional = optional

        assert self.rule is not None and isinstance(self.rule, Rule)
        assert self.criterion_rule_alias is None or isinstance(self.criterion_rule_alias, RuleAlias)

    def get_name(self):
        """
        Returns the name of the grammar. By default it uses the name of the token class in the criterion_rule_alias
        """
        return self.criterion_rule_alias.token_cls.__name__ if not self.name else self.name

    def get_grammar_criterion(self) -> RuleAlias:
        """
        Returns the criterion that defines this grammar/ that makes this grammar recognizable.
        """
        return self.criterion_rule_alias

    def validate_sequence(self, sequence: [RuleToken], index=0):
        """
        Validates the given sequence. If this is called by a parent, no index should be passed.
        It will call Rules that will call this method recursively.

        :raises GrammarInvalid

        :arg sequence - list of RuleTokens - they represent all tokens from an input text
        :arg index (default 0) - the current index of validation in the sequence

        :return: current index in sequence
        """
        try:
            # noinspection PyProtectedMember
            return self.rule._validate_sequence(sequence, index)
        except RuleNotFulfilled as e:
            # get the criterion of this grammar - it is a RuleAlias
            criterion = self.get_grammar_criterion()
            if not criterion or self.optional:
                return index

            # get list of elements between entrypoint and error
            error_index = e.sequence_index
            validated_tokens = sequence[index:error_index]
            validated_rule_alias = [t.rule_alias for t in validated_tokens]

            # the rule_alias that is responsible for the error
            error_src = e.rule_alias

            # raise an error if either the criterion for this grammar was already validated or
            # if that exact criterion threw the error
            if criterion in validated_rule_alias or criterion == error_src:
                raise GrammarInvalid('Invalid syntax for {} - {}'.format(self.get_name(), str(e)))

            return index
