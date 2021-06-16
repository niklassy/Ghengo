from decimal import Decimal

from django.db.models import IntegerField, FloatField, BooleanField, DecimalField, ManyToManyField, ManyToManyRel, \
    ForeignKey

from django_meta.project import AbstractModelField
from nlp.generate.argument import Kwarg
from nlp.generate.expression import ModelM2MAddExpression, ModelFactoryExpression
from nlp.generate.utils import to_function_name
from nlp.generate.variable import Variable
from nlp.vocab import NEGATIONS, POSITIVE_BOOLEAN_INDICATORS
from nlp.utils import get_verb_for_token, token_is_proper_noun


class Extractor(object):
    """
    The extractor is responsible to get valid data from a token. There may be a predetermined value that
    the extractor can use.
    """
    def __init__(self, test_case, predetermined_value, source):
        self.test_case = test_case
        self.predetermined_value = predetermined_value
        self.source = source

    def get_determined_value(self):
        raise NotImplementedError()

    def translate(self):
        return self.get_determined_value()


class ModelFieldExtractor(Extractor):
    """
    Extracts the value from a token for a given field of a model.
    """
    def __init__(self, test_case, predetermined_value, source, model_interface, field):
        super().__init__(test_case, predetermined_value, source)
        self.model_interface = model_interface
        self.field = field
        self.field_name = field.name

    def extract_number_for_field(self):
        """
        Returns the value of the source as a number. The predetermined value is most likely not correct here
        since the structure of sentences is different when numbers are used.
        """
        if not self.source:
            return str(self.get_default_value())

        root = self.source
        for child in self.get_all_children(root):
            if child.is_digit:
                return str(child)

        raise ValueError('There was not a number found for field {}'.format(self.field_name))

    def get_determined_value(self):
        """
        Check the type of the field and use different functions to extract the value.
        """
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
        """
        ForeignKeys should have a Variable as a value. So we need to search for previous statements in the test case
        that fit the model that this FK references.
        """
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
        """
        The default value is a simple string that removes ' and " from the edges.
        """
        value = str(self.predetermined_value)

        if len(value) > 0:
            if (value[0] == '"' and value[-1] == '"') or (value[0] == "'" and value[-1] == "'"):
                value = value[1:-1]

        return value

    def get_value_for_boolean_field(self):
        """
        This should return a boolean. In this case, we search for the verb and try to check if the source
        or the verb are negated.
        """
        verb = get_verb_for_token(self.source) if self.source else None

        if verb is None:
            return self.get_default_value() in POSITIVE_BOOLEAN_INDICATORS[self.source.lang_]

        verb_negated = any([child for child in verb.children if child.lemma_ in NEGATIONS[self.source.lang_]])
        source_negated = any([child for child in self.source.children if child.lemma_ in NEGATIONS[self.source.lang_]])

        return not verb_negated and not source_negated

    def get_value_for_integer_field(self):
        """Cast the value to an integer."""
        return int(self.extract_number_for_field())

    def get_value_for_float_field(self):
        """Cast to float"""
        return float(self.extract_number_for_field())

    def get_value_for_decimal_field(self):
        """Case to decimal."""
        return Decimal(self.extract_number_for_field())

    def get_all_children(self, token, prefilled_list=None):
        output = prefilled_list if prefilled_list is not None else []

        for child in token.children:
            output.append(child)
            self.get_all_children(child, output)

        return output

    def get_kwarg(self):
        """Wraps the value of this extractor in a Kwarg object."""
        if isinstance(self.field, (ManyToManyField, ManyToManyRel)):
            return None

        return Kwarg(self.field_name, self.translate())

    def append_side_effect_statements(self, statements):
        """
        In some cases, one statement is simply not enough. If there is a M2M field, we need to append
        objects in different statements. E.g.

        instance = factory()
        instance.m2m_field.add()
        """
        if isinstance(self.field, (ManyToManyField, ManyToManyRel)) and len(statements) > 0:
            factory_statement = statements[0]

            if not factory_statement.variable:
                factory_statement.generate_variable(self.test_case)

            value = self.predetermined_value
            for child in [value] + self.get_all_children(value):
                if child.is_digit or token_is_proper_noun(child):
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

                    m2m_expression = ModelM2MAddExpression(
                        model_instance_variable=factory_statement.variable,
                        field=self.field_name,
                        add_variable=variable
                    )
                    statements.append(m2m_expression.as_statement())

        return statements
