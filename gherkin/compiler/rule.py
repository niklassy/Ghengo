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
                self._validate_child_input(c)
        else:
            self._validate_child_input(child)

    def _validate_child_input(self, child):
        if not isinstance(child, Rule) and not isinstance(child, RuleClass):
            raise ValueError('You cannot use other children than Rule objects or RuleObjects around your own objects.')

    def _validate_sequence(self, sequence, index) -> int:
        raise NotImplementedError()

    def _validate_remote_object(self, rule_token: 'RuleToken', valid_cls: 'RuleClass'):
        assert isinstance(rule_token, RuleToken)

        obj = rule_token.token
        if not isinstance(obj, valid_cls.token_cls):
            keywords = valid_cls.get_keywords()

            if len(keywords) == 1:
                message = 'Expected "{}". Got "{}" instead. Near line {}.'.format(
                    keywords[0], rule_token.get_text(), rule_token.get_line_number())
            else:
                message = 'Expected one of {}. Got "{}" instead. Near line {}.'.format(
                    ', '.join(['"{}"'.format(k) for k in keywords]), rule_token.get_text(), rule_token.get_line_number()
                )

            raise RuleNotFulfilled(message)

    def validate_sequence(self, sequence):
        assert all([isinstance(el, RuleToken) for el in sequence]), 'Every entry in the passed sequence must of ' \
                                                                    'class "RuleToken"'

        self._validate_sequence(sequence, 0)


class Optional(Rule):
    def _validate_sequence(self, sequence, index) -> int:
        current_obj = sequence[index]

        try:
            if isinstance(self.child, Rule):
                return self.child._validate_sequence(sequence, index)
            else:
                self._validate_remote_object(current_obj, self.child)
                return index + 1
        except RuleNotFulfilled:
            return index


class OneOf(Rule):
    supports_list_as_children = True

    def _validate_sequence(self, sequence, index):
        errors = []

        for child in self.child:
            current_obj = sequence[index]

            try:
                if isinstance(child, Rule):
                    return child._validate_sequence(sequence, index)
                else:
                    self._validate_remote_object(current_obj, child)
            except RuleNotFulfilled as e:
                errors.append(e)

        if len(errors) == len(self.child):
            raise RuleNotFulfilled(str(errors[0]))

        return index + 1


class Repeatable(Rule):
    """min repeat?? x-y in init"""

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
                    self._validate_remote_object(current_obj, self.child)
                    index += 1
                rounds_done += 1
            except RuleNotFulfilled as e:
                break_error = e
                break

        if break_error and rounds_done < self.minimum:
            raise break_error

        return index


class Chain(Rule):
    supports_list_as_children = True

    def _validate_sequence(self, sequence, index):
        for entry in self.child:
            current_obj = sequence[index]

            if isinstance(entry, Rule):
                index = entry._validate_sequence(sequence, index)
            else:
                self._validate_remote_object(current_obj, entry)
                index += 1

        return index


class RuleClass(object):
    def __init__(self, token_cls):
        self.token_cls = token_cls

    def object_is_valid(self, obj):
        return isinstance(obj, self.token_cls)

    def get_line(self, obj):
        return obj.line.line_index

    def get_keywords(self):
        return self.token_cls.get_keywords()


class RuleToken(object):
    def __init__(self, token):
        self.token = token
        self.rule_class = RuleClass(token.__class__)

    def get_line_number(self):
        return self.token.line.line_index

    def get_text(self):
        return self.token.matched_keyword_full
