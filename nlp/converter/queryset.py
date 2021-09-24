from nlp.converter.model import ModelConverter
from nlp.converter.property import ModelCountProperty
from nlp.converter.wrapper import ReferenceTokenWrapper
from nlp.extractor.base import IntegerExtractor
from nlp.generate.argument import Argument, Kwarg
from nlp.generate.attribute import Attribute
from nlp.generate.constants import CompareChar
from nlp.generate.expression import Expression, CompareExpression, ModelQuerysetGetExpression, \
    ModelQuerysetBaseExpression, ModelQuerysetFilterExpression, ModelQuerysetAllExpression
from nlp.generate.statement import AssertStatement, AssignmentStatement
from nlp.generate.variable import Variable
from nlp.lookout.token import ComparisonLookout
from nlp.utils import token_is_plural, token_is_definite, token_is_indefinite, get_previous_token, token_is_noun, \
    tokens_are_equal


class QuerysetConverter(ModelConverter):
    """
    This converter can be used to translate text into a queryset statement.
    """
    def __init__(self, document, related_object, django_project, test_case):
        super().__init__(document, related_object, django_project, test_case)
        self.assignment_variable = Variable(
            self.get_variable_name(),
            self.model.value.name if self.model.value else '',
        )

    def get_document_compatibility(self):
        """
        If the model token is not a noun, it is unlikely that this converter matches.
        """
        compatibility = 1

        if not token_is_noun(self.model.token):
            compatibility *= 0.01

        return compatibility

    @property
    def has_query_kwargs(self):
        return len(self.extractors) > 0

    def get_queryset_expression(self):
        if not self.has_query_kwargs:
            return ModelQuerysetAllExpression(self.model.value)

        return ModelQuerysetFilterExpression(self.model.value, [])

    def get_variable_name(self):
        qs_statements = self.test_case.get_all_statements_with_expression(ModelQuerysetBaseExpression)

        return 'qs_{}'.format(len(qs_statements))

    def prepare_statements(self, statements):
        """
        Create a queryset statement. If there any extractor, filter for it. If there are none, simply get all.
        """
        expression = self.get_queryset_expression()
        statements.append(AssignmentStatement(variable=self.assignment_variable, expression=expression))
        return statements

    def handle_extractor(self, extractor, statements):
        super().handle_extractor(extractor, statements)

        if not self.has_query_kwargs:
            return

        qs_statement = statements[0]
        factory_kwargs = qs_statement.expression.function_kwargs

        extracted_value = self.extract_and_handle_output(extractor)
        kwarg = Kwarg(extractor.field_name, extracted_value)
        factory_kwargs.append(kwarg)


class ObjectQuerysetConverter(QuerysetConverter):
    """This converter can be used to create assert statements on the fields of a database entry."""
    def get_variable_name(self):
        other_get_statements = self.test_case.get_all_statements_with_expression(ModelQuerysetGetExpression)

        return '{}_{}'.format(self.model.value.name, len(other_get_statements))

    @property
    def has_query_kwargs(self):
        """Only consider the filter extractors for this property."""
        return len(self.get_filter_extractors()) > 0

    def get_document_compatibility(self):
        compatibility = super().get_document_compatibility()

        token_before_model = get_previous_token(self.model.token)
        if not token_before_model:
            return 0

        # check the token before the model token - since this converter references one exact instance of a model
        # it will be referenced in a definite way (the order, der Auftrag etc.) and not indefinite
        # (an order, ein Auftrag)
        if token_is_indefinite(token_before_model):
            compatibility *= 0.2
        elif token_is_definite(token_before_model):
            pass
        else:
            # the token before the model can be something else - these will most likely not fit though
            compatibility *= 0.5

        # since this will reference a single model entry, it is rather unlikely that this converter fits if the model
        # token is in plural
        if self.model.token and token_is_plural(self.model.token):
            compatibility *= 0.5

        return compatibility

    def get_queryset_expression(self):
        """
        This converter will always create a get queryset.
        """
        return ModelQuerysetGetExpression(self.model.value, [])

    def get_assert_extractors(self):
        """The last extractor will always be the value that is checked/ asserted."""
        return [self.extractors[-1]]

    def get_filter_extractors(self):
        """All but the last extractor are used to get the value from the database."""
        return self.extractors[:-1]

    def handle_extractor(self, extractor, statements):
        """
        If we filter for an extractor, handle the extractor normally. If it is used to assert, create an
        assert statement.
        """
        if extractor in self.get_filter_extractors():
            super().handle_extractor(extractor, statements)

        elif extractor in self.get_assert_extractors():
            exp = CompareExpression(
                Attribute(self.assignment_variable.get_reference(), extractor.field_name),
                CompareChar.EQUAL,
                Argument(extractor.extract_value()),
            )
            statement = AssertStatement(exp)
            statements.append(statement)

        else:
            raise ValueError('This should not happen.')


class CountQuerysetConverter(QuerysetConverter):
    """
    This converter can be used to create an assert statement for the count of a queryset.
    """
    def __init__(self, document, related_object, django_project, test_case):
        super().__init__(document, related_object, django_project, test_case)
        self.count = ModelCountProperty(self)

    def get_extractor_kwargs(self, argument_wrapper, extractor_cls):
        """Since the count token is extracted by a IntegerExtractor, remove kwargs that it does not need."""
        kwargs = super().get_extractor_kwargs(argument_wrapper, extractor_cls)
        if tokens_are_equal(argument_wrapper.token, self.count.token):
            del kwargs['model_wrapper']
            del kwargs['field_wrapper']
        return kwargs

    def prepare_converter(self):
        """Block the count token."""
        super().prepare_converter()
        self.block_token_as_reference(self.count.token)

    def get_extractor_class(self, argument_wrapper):
        """
        For everything related to the filter use the normal extractor classes. For the count token use an
        IntegerExtractor instead.
        """
        if tokens_are_equal(argument_wrapper.token, self.count.token):
            return IntegerExtractor
        return super().get_extractor_class(argument_wrapper)

    def get_document_compatibility(self):
        """If there is not count token, is is unlikely that this converter is compatible."""
        compatibility = super().get_document_compatibility()

        if not self.count.token:
            compatibility *= 0.2

        return compatibility

    def prepare_statements(self, statements):
        """
        In addition to the Queryset (created by the parent), create an assert statement to check the count
        of that queryset.
        """
        statements = super().prepare_statements(statements)
        qs_statement = statements[0]

        # extract the value of the count
        count_wrapper = ReferenceTokenWrapper(
            reference=self.count.value,
            token=self.count.token,
            source_represents_output=True,
        )
        count_extractor = self.get_extractor_instance(count_wrapper)
        count_value = self.extract_and_handle_output(count_extractor)

        # get the _comparison value (==, <= etc.)
        compare_lookout = ComparisonLookout(self.count.chunk, reverse=False)

        # create expression and statement
        expression = CompareExpression(
            Attribute(qs_statement.variable.get_reference(), 'count()'),
            compare_lookout.get_comparison_for_value(count_value),
            Argument(count_value),
        )
        statement = AssertStatement(expression)
        statements.append(statement)

        return statements


class ExistsQuerysetConverter(QuerysetConverter):
    """
    This converter creates a queryset and an assert statement to check if that queryset exists.
    """
    def prepare_statements(self, statements):
        statements = super().prepare_statements(statements)
        qs_statement = statements[0]

        statement = AssertStatement(
            Expression(Attribute(qs_statement.variable.get_reference(), 'exists()'))
        )
        statements.append(statement)

        return statements
