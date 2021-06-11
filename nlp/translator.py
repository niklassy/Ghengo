from decimal import Decimal

from django.db.models import IntegerField, FloatField, BooleanField, DecimalField, ManyToManyField, ManyToManyRel

from nlp.utils import get_verb_for_token


class Translator(object):
    def __init__(self, test_case, predetermined_value, source):
        self.test_case = test_case
        self.predetermined_value = predetermined_value
        self.source = source

    def get_determined_value(self):
        raise NotImplementedError()


class ModelFieldTranslator(Translator):
    def __init__(self, test_case, predetermined_value, source, model, field):
        super().__init__(test_case, predetermined_value, source)
        self.model = model
        self.field = field

    def get_determined_value(self):
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

    def get_default_value(self):
        return str(self.predetermined_value)

    def get_value_for_m2m(self):
        return self.get_determined_value()

    def get_value_for_boolean_field(self):
        verb = get_verb_for_token(self.source)

        if verb is None:
            return self.get_default_value() in ['1', 'True', 'true']

        return not any([child for child in verb.children if child.lemma_ in ['kein', 'nicht']])

    def get_value_for_integer_field(self):
        return int(self.get_default_value())

    def get_value_for_float_field(self):
        return float(self.get_default_value())

    def get_value_for_decimal_field(self):
        return Decimal(self.get_default_value())
