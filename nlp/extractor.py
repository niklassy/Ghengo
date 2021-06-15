from decimal import Decimal

from django.db.models import IntegerField, FloatField, BooleanField, DecimalField, ManyToManyField, ManyToManyRel, \
    ForeignKey

from django_meta.project import AbstractModelField
from generate.suite import Statement, ModelM2MAddExpression, Kwarg, ModelFactoryExpression
from generate.utils import to_function_name
from nlp.generate.variable import Variable
from nlp.utils import get_verb_for_token


class Extractor(object):
    def __init__(self, test_case, predetermined_value, source):
        self.test_case = test_case
        self.predetermined_value = predetermined_value
        self.source = source

    def get_determined_value(self):
        raise NotImplementedError()

    def translate(self):
        return self.get_determined_value()


class ModelFieldExtractor(Extractor):
    def __init__(self, test_case, predetermined_value, source, model, field):
        super().__init__(test_case, predetermined_value, source)
        self.model = model
        self.field = field
        self.field_name = field.name

    def extract_number_for_field(self):
        if not self.source:
            return str(self.get_default_value())

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

        if isinstance(self.field, ForeignKey):
            return self.get_value_for_fk_field()

        default_value = self.get_default_value()
        if default_value is not None:
            return str(default_value)

        return None

    def get_value_for_fk_field(self):
        value = to_function_name(self.get_default_value())
        related_model = self.field.related_model

        # search for a previous statement where an entry of that model was created and use its variable
        for statement in self.test_case.statements:
            if not isinstance(statement.expression, ModelFactoryExpression) or not statement.variable:
                continue

            expression_model = statement.expression.model_interface.model
            if statement.string_matches_variable(value) and expression_model == related_model:
                return statement.variable.copy()

        return value

    def get_default_value(self):
        value = str(self.predetermined_value)

        if len(value) > 0:
            if (value[0] == '"' and value[-1] == '"') or (value[0] == "'" and value[-1] == "'"):
                value = value[1:-1]

        return value

    def get_value_for_boolean_field(self):
        verb = get_verb_for_token(self.source) if self.source else None

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

        return Kwarg(self.field_name, self.translate())

    def append_side_effect_statements(self, statements):
        if isinstance(self.field, (ManyToManyField, ManyToManyRel)) and len(statements) > 0:
            factory_statement = statements[0]

            if not factory_statement.variable:
                factory_statement.generate_variable(self.test_case)

            value = self.predetermined_value
            for child in [value] + self.get_all_children(value):
                if child.is_digit or child.pos_ == 'PROPN':
                    related_model = self.field.related_model
                    variable = Variable(
                        name_predetermined=str(child),
                        reference_string=related_model.__name__,
                    )

                    for statement in self.test_case.statements:
                        expression = statement.expression
                        if not isinstance(expression, ModelFactoryExpression):
                            continue

                        # check if the value can become the variable and if the expression has the same model
                        expression_model = expression.model_interface.model
                        if statement.string_matches_variable(str(child)) and expression_model == related_model:
                            variable = statement.variable.copy()
                            break

                    expression = ModelM2MAddExpression(
                        model=factory_statement.variable,
                        field=self.field_name,
                        variable=variable,
                    )
                    statement = Statement(expression)
                    statements.append(statement)

        return statements
