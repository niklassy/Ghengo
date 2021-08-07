from nlp.converter.base.converter import ClassConverter
from nlp.converter.property import ReferenceModelVariableProperty, ReferenceModelProperty, NewModelProperty, \
    NewModelVariableProperty
from nlp.extractor.fields_model import get_model_field_extractor
from nlp.generate.argument import Argument, Kwarg
from nlp.generate.attribute import Attribute
from nlp.generate.expression import ModelSaveExpression, ModelFactoryExpression, Expression, CompareExpression
from nlp.generate.statement import ModelFieldAssignmentStatement, AssignmentStatement, AssertStatement
from nlp.locator import ComparisonLocator
from nlp.searcher import ModelFieldSearcher
from nlp.utils import get_root_of_token, token_is_noun, token_is_plural, get_noun_chunk_of_token


class ModelConverter(ClassConverter):
    """
    This is the base converter for model related stuff.
    """
    field_searcher_classes = [ModelFieldSearcher]

    def __init__(self, document, related_object, django_project, test_case):
        super().__init__(document, related_object, django_project, test_case)
        self.model = NewModelProperty(self)
        self.variable = NewModelVariableProperty(self)

    def prepare_converter(self):
        """The model and variable token are disabled as an argument."""
        self.block_token_as_argument(self.model.token)
        self.block_token_as_argument(self.variable.token)

    def get_searcher_kwargs(self):
        """Add the model to the searcher."""
        return {'model_adapter': self.model.value}

    def get_extractor_class(self, argument_wrapper):
        """The extractor class needs to be determined based on the kwarg_representative which is a model field."""
        return get_model_field_extractor(argument_wrapper.representative.field)

    def get_extractor_kwargs(self, argument_wrapper, extractor_cls):
        """Add the model and the field to the kwargs."""
        kwargs = super().get_extractor_kwargs(argument_wrapper, extractor_cls)
        kwargs['model_adapter'] = self.model.value
        kwargs['field_adapter'] = argument_wrapper.representative
        return kwargs


class ModelFactoryConverter(ModelConverter):
    """
    This converter will convert a document into a model factory statement and everything that belongs to it.
    """
    can_use_datatables = True

    def prepare_statements(self, statements):
        """
        Before working with the extractors, create an assignment statement with the model factory. That statement
        will be used to add the values of the extractors.
        """
        expression = ModelFactoryExpression(model_adapter=self.model.value, factory_kwargs=[])
        variable = self.variable.value
        statement = AssignmentStatement(variable=variable, expression=expression)
        return [statement]

    def get_document_compatibility(self):
        compatibility = 1

        if not self.model.value.exists_in_code:
            compatibility *= 0.8

        # models are normally displayed by nouns
        if not token_is_noun(self.model.token):
            compatibility *= 0.01

        if self.model.chunk and len(self.get_noun_chunks()) > 0 and self.model.chunk != self.get_noun_chunks()[0]:
            compatibility *= 0.1

        # If the root of the document is a finites Modalverb (e.g. sollte) it is rather unlikely that the creation of
        # a model is meant
        root = get_root_of_token(self.model.token)
        if root and root.tag_ == 'VMFIN':
            compatibility *= 0.4

        return compatibility

    def handle_extractor(self, extractor, statements):
        """
        For each extractor, get the factory statement that was created in `prepare_statements`. After that
        extract the value from the extractor and add it an a Kwarg to the factory.
        """
        super().handle_extractor(extractor, statements)
        factory_kwargs = statements[0].expression.function_kwargs

        extracted_value = self.extract_and_handle_output(extractor)

        kwarg = Kwarg(extractor.field_name, extracted_value)
        factory_kwargs.append(kwarg)


class ModelVariableReferenceConverter(ModelConverter):
    """
    This converter is used in cases where steps simply reference other steps where a variable was defined:
        - Given a user Alice ...
        - And Alice has a password "Haus1234"
    """
    def __init__(self, document, related_object, django_project, test_case):
        super().__init__(document, related_object, django_project, test_case)
        self.model_in_text = NewModelProperty(self)
        self.model = ReferenceModelProperty(self)
        self.variable = ReferenceModelVariableProperty(self)

        # the value of the variable is important for the model
        self.variable.calculate_value()

    def get_variable_model_adapter(self):
        """
        Returns the model adapter of the variable that this references. Returns none if there is no variable.
        """
        if not self.variable.value:
            return None

        variable_instance = self.variable.value
        return variable_instance.value.model_adapter

    def get_document_compatibility(self):
        """Only if a previous variable exists, this converter makes sense."""
        variable_model_adapter = self.get_variable_model_adapter()
        if variable_model_adapter and variable_model_adapter.models_are_equal(self.model_in_text.value):
            return 1
        return 0

    def handle_extractor(self, extractor, statements):
        """Each value that was extracted represents a statement in which the value is set on the model instance."""
        super().handle_extractor(extractor, statements)
        extracted_value = self.extract_and_handle_output(extractor)

        statement = ModelFieldAssignmentStatement(
            variable=self.variable.value,
            assigned_value=Argument(value=extracted_value),
            field_name=extractor.field_name,
        )
        statements.append(statement)

    def finish_statements(self, statements):
        """At the end there has to be a `save` call."""
        statements = super().finish_statements(statements)
        # only add a save statement if any model field was changed
        if len(statements) > 0:
            statements.append(ModelSaveExpression(self.variable.value).as_statement())
        return statements


class AssertPreviousModelConverter(ModelConverter):
    """
    This converter can be used to check fields from the variable of a model that was previously created.
    """
    def __init__(self, document, related_object, django_project, test_case):
        super().__init__(document, related_object, django_project, test_case)
        self.variable = ReferenceModelVariableProperty(self)
        self.model = ReferenceModelProperty(self)

        # the value of the variable is important for the model
        self.variable.calculate_value()

    def get_document_compatibility(self):
        compatibility = super().get_document_compatibility()

        if not self.variable.token:
            compatibility *= 0.2

        # since this references a single entry, it is unlikely that this fits if multiple model entries are mentioned
        if token_is_plural(self.model.token):
            compatibility *= 0.5

        return compatibility

    def prepare_statements(self, statements):
        # we need to refresh the data before checking the values
        statements.append(
            Expression(Attribute(self.variable.value, 'refresh_from_db()')).as_statement()
        )

        return statements

    def handle_extractor(self, extractor, statements):
        """For each extractor, use the field to create a compare expression."""
        chunk = get_noun_chunk_of_token(extractor.source, self.document)
        compare_locator = ComparisonLocator(chunk or self.document, reverse=False)
        extracted_value = extractor.extract_value()

        exp = CompareExpression(
            Attribute(self.variable.value, extractor.field_name),
            compare_locator.get_comparison_for_value(extracted_value),
            Argument(extracted_value),
        )
        statement = AssertStatement(exp)
        statements.append(statement)
