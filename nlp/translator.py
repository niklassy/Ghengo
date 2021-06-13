from decimal import Decimal

from django.db.models import IntegerField, FloatField, BooleanField, DecimalField, ManyToManyField, ManyToManyRel

from django_meta.project import AbstractModelField
from generate.suite import Statement, ModelM2MAddExpression, Variable, Kwarg, ModelFactoryExpression
from generate.utils import to_function_name
from nlp.generate.context import VariableContext
from nlp.utils import get_verb_for_token


class Translator(object):
    def __init__(self, test_case, predetermined_value, source):
        self.test_case = test_case
        self.predetermined_value = predetermined_value
        self.source = source

    def value_is_variable(self):
        return self.test_case.variable_defined(self.get_value_as_function_name())

    def get_value_as_function_name(self):
        value = self.get_determined_value()
        if isinstance(value, bool):
            return ''

        return to_function_name(str(self.get_determined_value()))

    def get_determined_value(self):
        raise NotImplementedError()

    def translate(self):
        if self.value_is_variable():
            return self.get_value_as_function_name()

        return self.get_determined_value()


class ModelFieldTranslator(Translator):
    def __init__(self, test_case, predetermined_value, source, model, field):
        super().__init__(test_case, predetermined_value, source)
        self.model = model
        self.field = field
        self.field_name = field.name

    def extract_number_for_field(self):
        root = self.source
        for child in self.get_all_children(root):
            if child.is_digit:
                return str(child)
        raise ValueError('There was not a number found for field {}'.format(self.field_name))

    def get_determined_value(self):
        if isinstance(self.field, AbstractModelField):
            try:
                value = self.extract_number_for_field()
                return int(value)
            except ValueError:
                pass

        if isinstance(self.field, IntegerField):
            return self.get_value_for_integer_field()

        if isinstance(self.field, FloatField):
            return self.get_value_for_float_field()

        if isinstance(self.field, BooleanField):
            return self.get_value_for_boolean_field()

        if isinstance(self.field, DecimalField):
            return self.get_value_for_decimal_field()

        default_value = self.get_default_value()
        if default_value is not None:
            return str(default_value)

        return None

    def get_default_value(self):
        value = str(self.predetermined_value)

        if len(value) > 0:
            if (value[0] == '"' and value[-1] == '"') or (value[0] == "'" and value[-1] == "'"):
                value = value[1:-1]

        return value

    def get_value_for_boolean_field(self):
        verb = get_verb_for_token(self.source)

        if verb is None:
            return self.get_default_value() in ['1', 'True', 'true']

        return not any([child for child in verb.children if child.lemma_ in ['kein', 'nicht']])

    def get_value_for_integer_field(self):
        return int(self.extract_number_for_field())

    def get_value_for_float_field(self):
        return float(self.extract_number_for_field())

    def get_value_for_decimal_field(self):
        return Decimal(self.extract_number_for_field())

    def get_all_children(self, token, prefilled_list=None):
        output = prefilled_list if prefilled_list is not None else []

        for child in token.children:
            output.append(child)
            self.get_all_children(child, output)

        return output

    def get_kwarg(self):
        if isinstance(self.field, (ManyToManyField, ManyToManyRel)):
            return None

        return Kwarg(self.field_name, self.translate(), as_variable=self.value_is_variable())

    def append_side_effect_statements(self, statements):
        if isinstance(self.field, (ManyToManyField, ManyToManyRel)) and len(statements) > 0:
            factory_statement = statements[0]

            if not factory_statement.variable:
                factory_statement.generate_variable(self.test_case)

            value = self.predetermined_value
            for child in [value] + self.get_all_children(value):
                if child.is_digit or child.pos_ == 'PROPN':
                    related_model = self.field.related_model
                    reference_string = related_model.__name__

                    for statement in self.test_case.statements:
                        expression = statement.expression
                        if not isinstance(expression, ModelFactoryExpression):
                            continue

                        if statement.uses_variable(str(child)) and expression.model_interface.model == related_model:
                            reference_string = statement.variable_context.reference_string
                            break

                    variable_context = VariableContext(
                        source_token=child,
                        variable_name_predetermined=str(child),
                        reference_string=reference_string,
                    )

                    expression = ModelM2MAddExpression(
                        model=factory_statement.variable,
                        field=self.field_name,
                        variable_context=variable_context,
                    )
                    statement = Statement(expression)
                    statements.append(statement)

        return statements
