class RuleNotFulfilled(Exception):
    pass


class Rule(object):
    supports_list_as_children = False

    def __init__(self, child):
        self.child = child

        if isinstance(child, list) and not self.supports_list_as_children:
            raise ValueError('A {} does not support a list of objects as a child'.format(self.__class__.__name__))

        # validate the given child
        if isinstance(child, list):
            for c in child:
                self._validate_init_child(c)
        else:
            self._validate_init_child(child)

    def _validate_init_child(self, child):
        """Validation on __init__"""
        if not isinstance(child, Rule) and not isinstance(child, RuleClass):
            raise ValueError('You cannot use other children than Rule objects or RuleObjects around your own objects.')

    def _validate_sequence(self, sequence, index) -> int:
        """
        Implemented by each rule. Does the validation of a given sequence. Can be called recursively.
        The index represents the current index at which the sequence is checked.
        """
        raise NotImplementedError()

    def _validate_rule_token(self, rule_token: 'RuleToken', rule_class: 'RuleClass'):
        """
        Validates a given rule token belongs to a rule class. If not a RuleNotFulfilled is risen.
        """
        assert isinstance(rule_token, RuleToken)
        assert rule_class == RuleClass

        if not rule_class.rule_token_is_valid(rule_token.token):
            keywords = rule_class.get_keywords()

            if len(keywords) == 1:
                message = 'Expected "{}". Got "{}" instead. {}.'.format(
                    keywords[0], rule_token.get_text(), rule_token.get_place_to_search())
            else:
                message = 'Expected one of {}. Got "{}" instead. {}.'.format(
                    ', '.join(['"{}"'.format(k) for k in keywords]), rule_token.get_text(),
                    rule_token.get_place_to_search()
                )

            raise RuleNotFulfilled(message)

    def validate_sequence(self, sequence: ['RuleToken']):
        """
        Public function to validate a given sequence. May raise a RuleNotFulfilled
        """
        assert all([isinstance(el, RuleToken) for el in sequence]), 'Every entry in the passed sequence must of ' \
                                                                    'class "RuleToken"'

        self._validate_sequence(sequence, 0)


class Optional(Rule):
    """
    Can be used to mark something a token as optional.
    """
    def _validate_sequence(self, sequence, index) -> int:
        current_obj = sequence[index]

        try:
            if isinstance(self.child, Rule):
                return self.child._validate_sequence(sequence, index)
            else:
                self._validate_rule_token(current_obj, self.child)
                return index + 1
        except RuleNotFulfilled:
            return index


class OneOf(Rule):
    """
    Can be used as an OR operation: Any token that is passed is valid. If none exists, an error is thrown.
    """
    supports_list_as_children = True

    def _validate_sequence(self, sequence, index):
        errors = []

        for child in self.child:
            current_obj = sequence[index]

            try:
                if isinstance(child, Rule):
                    return child._validate_sequence(sequence, index)
                else:
                    self._validate_rule_token(current_obj, child)
            except RuleNotFulfilled as e:
                errors.append(e)

        if len(errors) == len(self.child):
            raise RuleNotFulfilled(str(errors[0]))

        return index + 1


class Repeatable(Rule):
    """Allows any amount of repetition of the passed child. If it is optional, minimum=0 can be passed."""

    def __init__(self, child, minimum=1):
        super().__init__(child)
        self.minimum = minimum

        assert not isinstance(child, list), 'You must not use a list as a child of Repeatable, use Chain ' \
                                            'or OneOf instead.'
        assert not isinstance(child, Optional), 'You must not use Optional as a child of ' \
                                                'Repeatable. Use minimum=0 instead.'

    def _validate_sequence(self, sequence, index):
        rounds_done = 0

        while True:
            current_obj = sequence[index]

            try:
                if isinstance(self.child, Rule):
                    index = self.child._validate_sequence(sequence, index)
                else:
                    self._validate_rule_token(current_obj, self.child)
                    index += 1
                rounds_done += 1
            except RuleNotFulfilled as e:
                break_error = e
                break

        if break_error and rounds_done < self.minimum:
            raise break_error

        return index


class Chain(Rule):
    """
    Allows a specific order of tokens to be checked. If the exact order is not correct, an error is thrown.
    """
    supports_list_as_children = True

    def _validate_sequence(self, sequence, index):
        for entry in self.child:
            current_obj = sequence[index]

            if isinstance(entry, Rule):
                index = entry._validate_sequence(sequence, index)
            else:
                self._validate_rule_token(current_obj, entry)
                index += 1

        return index


class RuleClass(object):
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


class RuleToken(object):
    """
    This is a wrapper around any custom token object. It is used to allow rules to get the line_number and the
    text of a token. For this project, the class could be removed, but it is a nice wrapper for future usage.
    """
    def __init__(self, token):
        self.token = token
        self.rule_class = RuleClass(token.__class__)

    def get_place_to_search(self) -> str:
        """Is used by rules to add information where a token can be found."""
        return 'Near line: {}'.format(self.token.line.line_index)

    def get_text(self) -> str:
        """Defines how to represent a token in text. It is used by rules to display what the current value is."""
        return self.token.matched_keyword_full
