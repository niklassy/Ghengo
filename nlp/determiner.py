from django.db.models import BooleanField, IntegerField
from spacy.tokens import Token, Span

from nlp.utils import token_references, is_proper_noun_of


class FieldValueDeterminer(object):
    """
    A FieldValueDeterminer can be used to determine the value of a field in a model with a given value source.

    So there is an input into this class
    """
    def __init__(self, model, value_source, field):
        self.field_name = field.name
        self.field = field
        self.model = model
        self._value_source = value_source

    @property
    def value_source(self):
        return self._value_source

    def value_to_python(self):
        return str(self.determine_value())

    def value_source_is_negated(self):
        return False

    def value_can_be_function_name(self):
        return isinstance(self.value_to_python(), str)

    def determine_value(self):
        return self.value_source


class StringFieldValueDeterminer(FieldValueDeterminer):
    def __init__(self, model, value_string, field):
        assert isinstance(value_string, str)
        super().__init__(model, value_string, field)


class TokenFieldValueDeterminer(FieldValueDeterminer):
    def __init__(self, model, value_token, field):
        assert isinstance(value_token, Token)
        super().__init__(model, value_token, field)


class SpanFieldValueDeterminer(FieldValueDeterminer):
    def __init__(self, model, value_source, field):
        assert isinstance(value_source, Span)
        super().__init__(model, value_source, field)

    def determine_value(self):
        for token in self.value_source:
            if is_proper_noun_of(token, self.value_source.root):
                return token
        return None

    def value_to_python(self):
        if isinstance(self.field, BooleanField):
            return not self.value_source_is_negated()

        if isinstance(self.field, IntegerField):
            root = self.value_source.root
            for child in root.children:
                if child.is_digit:
                    return int(str(child))
            return ValueError('There was not a number found for field {}'.format(self.field_name))

        determined_value = self.determine_value()
        if determined_value is None:
            return None

        return str(determined_value)

    def value_source_is_negated(self):
        verb = self.get_verb_for_token(self.value_source.root)
        if verb is None:
            return False

        return any([child for child in verb.children if child.lemma_ in ['kein', 'nicht']])

    def get_verb_for_token(self, token):
        if token.pos_ == 'VERB':
            return token

        if token.head is None or token.head == token:
            return None

        return self.get_verb_for_token(token.head)
