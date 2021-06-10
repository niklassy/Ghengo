from decimal import Decimal

from spacy.tokens import Token, Span

from generate.utils import camel_to_snake_case
from nlp.utils import is_proper_noun_of, get_verb_for_token


class FieldValueDeterminer(object):
    """
    A FieldValueDeterminer can be used to determine the value of a field in a model with a given value source.

    So there is an input into this class
    """
    def __init__(self, model, source, field):
        self.field_name = field.name
        self.field = field
        self.model = model
        self._source = source

    @property
    def source(self):
        return self._source

    def value_to_python(self):
        field_cls_snake_case = camel_to_snake_case(self.field.__class__.__name__)
        for_field_fn = getattr(self, 'get_value_for_{}'.format(field_cls_snake_case), None)

        if for_field_fn is not None:
            return for_field_fn()

        return str(self.get_default_value())

    def value_source_is_negated(self):
        return not self.get_value_for_boolean_field()

    def value_can_be_function_name(self):
        return isinstance(self.value_to_python(), str)

    def get_default_value(self):
        return self.source

    def get_value_for_boolean_field(self):
        return self.source in ['1', 'True', 'true']

    def get_value_for_integer_field(self):
        return int(self.source)

    def get_value_for_float_field(self):
        return float(self.source)

    def get_value_for_decimal_field(self):
        return Decimal(self.source)


class StringFieldValueDeterminer(FieldValueDeterminer):
    def __init__(self, model, value_string, field):
        assert isinstance(value_string, str)
        super().__init__(model, value_string, field)


class TokenFieldValueDeterminer(FieldValueDeterminer):
    def __init__(self, model, value_token, field):
        assert isinstance(value_token, Token)
        super().__init__(model, value_token, field)

    @property
    def source(self):
        return str(self._source)


class SpanFieldValueDeterminer(FieldValueDeterminer):
    def __init__(self, model, value_source, field):
        assert isinstance(value_source, Span)
        super().__init__(model, value_source, field)

    def extract_number_for_field(self):
        root = self.source.root
        for child in root.children:
            if child.is_digit:
                return str(child)
        return ValueError('There was not a number found for field {}'.format(self.field_name))

    def get_value_for_integer_field(self):
        return int(self.extract_number_for_field())

    def get_value_for_boolean_field(self):
        verb = get_verb_for_token(self.source.root)
        if verb is None:
            return False

        return not any([child for child in verb.children if child.lemma_ in ['kein', 'nicht']])

    def get_value_for_float_field(self):
        return float(self.extract_number_for_field())

    def get_value_for_decimal_field(self):
        return Decimal(self.extract_number_for_field())

    def get_default_value(self):
        for token in self.source:
            if is_proper_noun_of(token, self.source.root):
                return token
        return None
