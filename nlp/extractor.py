from decimal import Decimal

from django.db.models import IntegerField, FloatField, BooleanField, DecimalField, ManyToManyField, ManyToManyRel
from spacy.tokens import Token, Span

from nlp.utils import is_proper_noun_of, get_verb_for_token


class Extractor(object):
    """
    This is the base class that can be used to extract data from spacy spans, tokens or documents.

    They all get a source (the spacy object) and they hold functions to extract python values from it.
    """
    def __init__(self, source):
        self._source = source

    @property
    def source(self):
        return self._source

    @property
    def source_as_str(self):
        return str(self.source)

    def extract_python_value(self):
        return str(self.get_default_value())

    def value_source_is_negated(self):
        return not bool(self.get_default_value())

    def value_can_be_function_name(self):
        return True

    def get_default_value(self):
        return self.source


class ModelFieldExtractor(Extractor):
    """
    This is the base extractor that handles strings as a source. It will extract python values for model fields.

    E.g. a model Order, a field number and a text
        => The extractor will try to get a value that is valid for the field `number` and return it.
    """
    def __init__(self, model, source, field):
        super().__init__(source)
        self.field_name = field.name
        self.field = field
        self.model = model

    def value_source_is_negated(self):
        return not self.get_value_for_boolean_field()

    def value_can_be_function_name(self):
        return isinstance(self.extract_python_value(), str)

    def extract_python_value(self):
        if isinstance(self.field, IntegerField):
            return self.get_value_for_integer_field()

        if isinstance(self.field, FloatField):
            return self.get_value_for_float_field()

        if isinstance(self.field, BooleanField):
            return self.get_value_for_boolean_field()

        if isinstance(self.field, DecimalField):
            return self.get_value_for_decimal_field()

        if isinstance(self.field, (ManyToManyField, ManyToManyRel)):
            return self.get_value_for_m2m()

        default_value = self.get_default_value()
        if default_value is not None:
            return str(default_value)

        return None

    def get_value_for_m2m(self):
        return self.source_as_str

    def get_value_for_boolean_field(self):
        return self.source_as_str in ['1', 'True', 'true']

    def get_value_for_integer_field(self):
        return int(self.source_as_str)

    def get_value_for_float_field(self):
        return float(self.source_as_str)

    def get_value_for_decimal_field(self):
        return Decimal(self.source_as_str)


class SpanModelFieldExtractor(ModelFieldExtractor):
    """
    Since Spans can hold a lot more information than strings or Tokens this Extractor can do a lot more than
    ModelFieldExtractor.
    """
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
