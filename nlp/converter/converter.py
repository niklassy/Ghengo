from django_meta.api import UrlPatternAdapter
from django_meta.model import AbstractModelAdapter, AbstractModelFieldAdapter
from nlp.converter.base_converter import Converter
from nlp.converter.property import NewModelProperty, ReferenceModelVariableProperty, \
    ReferenceModelProperty, UserReferenceVariableProperty, ModelWithUserProperty, \
    MethodProperty, FileProperty, NewFileVariableProperty, NewModelVariableProperty
from nlp.extractor.base import StringExtractor
from nlp.extractor.fields_rest_api import get_api_model_field_extractor
from nlp.extractor.fields_model import get_model_field_extractor
from nlp.generate.argument import Kwarg, Argument
from nlp.generate.attribute import Attribute
from nlp.generate.expression import ModelFactoryExpression, ModelSaveExpression, RequestExpression, APIClientExpression, \
    APIClientAuthenticateExpression, CreateUploadFileExpression
from nlp.generate.statement import AssignmentStatement, ModelFieldAssignmentStatement
from nlp.generate.variable import Variable
from nlp.locator import FileContentLocator
from nlp.searcher import ModelFieldSearcher, NoConversionFound, UrlSearcher, SerializerFieldSearcher
from nlp.utils import get_non_stop_tokens, get_noun_chunk_of_token, token_is_noun, get_root_of_token, \
    NoToken


class ClassKwargRepresentative:
    """
    This class is used in converters to have an instance that holds a representative for a __init__ argument
    (e.g. a field from a model) and a token. The token was used to find the representative.
    """
    def __init__(self, token, representative):
        self.token = token
        self.representative = representative


class ClassConverter(Converter):
    field_searcher_classes = []

    def __init__(self, document, related_object, django_project, test_case):
        super().__init__(document, related_object, django_project, test_case)
        self._fields = None

    def token_used_in_property(self, token):
        return False

    def token_can_be_class_kwarg(self, token):
        # first word is always a keyword from Gherkin
        if self.document[0] == token:
            return False

        if self.token_used_in_property(token):
            return False

        if token.pos_ != 'ADJ' and token.pos_ != 'NOUN' and token.pos_ != 'VERB' and token.pos_ != 'ADV':
            if token.pos_ != 'PROPN':
                return False

            if self.token_can_be_class_kwarg(token.head):
                return False

        # verbs with aux are fine (is done, ist abgeschlossen)
        if token.pos_ == 'VERB' and token.head.pos_ != 'AUX':
            return False

        return True

    def get_searcher_kwargs(self):
        return {}

    def search_for_kwarg(self, span, token):
        for index, searcher_class in enumerate(self.field_searcher_classes):
            no_fallback = index < len(self.field_searcher_classes) - 1
            searcher_kwargs = self.get_searcher_kwargs()

            if span:
                span_searcher = searcher_class(text=str(span), src_language=self.language)

                try:
                    return span_searcher.search(raise_exception=True, **searcher_kwargs)
                except NoConversionFound:
                    pass

                root_searcher = searcher_class(text=str(span.root.lemma_), src_language=self.language)
                try:
                    return root_searcher.search(raise_exception=bool(token), **searcher_kwargs)
                except NoConversionFound:
                    pass

            if token:
                token_searcher = searcher_class(text=str(token), src_language=self.language)
                try:
                    return token_searcher.search(raise_exception=no_fallback, **searcher_kwargs)
                except NoConversionFound:
                    pass

        return None

    def get_class_kwarg_names(self) -> [ClassKwargRepresentative]:
        if self._fields is None:
            class_kwargs_representatives = []

            for token in get_non_stop_tokens(self.document):
                if not self.token_can_be_class_kwarg(token):
                    continue

                chunk = get_noun_chunk_of_token(token, self.document)
                kwarg_representative = self.search_for_kwarg(chunk, token)

                if kwarg_representative in [class_kw.representative for class_kw in class_kwargs_representatives]:
                    continue

                class_kwarg = ClassKwargRepresentative(representative=kwarg_representative, token=token)
                class_kwargs_representatives.append(class_kwarg)
            self._fields = class_kwargs_representatives
        return self._fields

    def get_extractor_class(self, kwarg_representative):
        raise NotImplementedError()

    def get_extractor_kwargs(self, kwarg_representative, token, extractor_cls):
        return {'test_case': self.test_case, 'source': token, 'document': self.document}

    def get_extractor_instance(self, kwarg_representative, token):
        extractor_class = self.get_extractor_class(kwarg_representative=kwarg_representative)
        kwargs = self.get_extractor_kwargs(
            kwarg_representative=kwarg_representative,
            extractor_cls=extractor_class,
            token=token,
        )

        return extractor_class(**kwargs)

    def get_extractors(self):
        class_kwarg_names = self.get_class_kwarg_names()

        if len(class_kwarg_names) == 0:
            return []

        if self._extractors is None:
            extractors = []

            for kwarg in class_kwarg_names:
                extractor_instance = self.get_extractor_instance(
                    kwarg_representative=kwarg.representative,
                    token=kwarg.token,
                )
                extractors.append(extractor_instance)

            self._extractors = extractors
        return self._extractors

    def get_statements_from_datatable(self):
        statements = []
        datatable = self.related_object.argument
        column_names = datatable.get_column_names()

        for row in datatable.rows:
            extractors_copy = self.extractors.copy()

            for index, cell in enumerate(row.cells):
                kwarg_representative = self.search_for_kwarg(span=None, token=column_names[index])
                extractor_instance = self.get_extractor_instance(
                    kwarg_representative=kwarg_representative,
                    token=cell.value,
                )
                extractors_copy.append(extractor_instance)

            statements += self.get_statements_from_extractors(extractors_copy)

        return statements


class ModelConverter(ClassConverter):
    """
    This is the base converter for model related stuff.
    """
    field_searcher_classes = [ModelFieldSearcher]

    def __init__(self, document, related_object, django_project, test_case):
        super().__init__(document, related_object, django_project, test_case)
        self.model = NewModelProperty(self)
        self.variable = NewModelVariableProperty(self)

    def token_used_in_property(self, token):
        """The token may be a model or represent the variable."""
        return token == self.model.token or self.variable.token == token

    def get_searcher_kwargs(self):
        """Add the model to the searcher."""
        return {'model_adapter': self.model.value}

    def get_extractor_class(self, kwarg_representative):
        """The extractor class needs to be determined based on the kwarg_representative which is a model field."""
        return get_model_field_extractor(kwarg_representative)

    def get_extractor_kwargs(self, kwarg_representative, token, extractor_cls):
        """Add the model and the field to the kwargs."""
        kwargs = super().get_extractor_kwargs(kwarg_representative, token, extractor_cls)
        kwargs['model_adapter'] = self.model.value
        kwargs['field'] = kwarg_representative
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

        if isinstance(self.model.value, AbstractModelAdapter):
            compatibility *= 0.8

        # models are normally displayed by nouns
        if not token_is_noun(self.model.token):
            compatibility *= 0.01

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

        extracted_value = extractor.extract_value()
        if extracted_value is None:
            return

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
        self.variable = ReferenceModelVariableProperty(self)
        self.model = ReferenceModelProperty(self)

        # the value of the variable is important for the model
        self.variable.calculate_value()

    def get_document_compatibility(self):
        """Only if a previous variable exists, this converter makes sense."""
        if self.variable.value:
            return 1
        return 0

    def handle_extractor(self, extractor, statements):
        """Each value that was extracted represents a statement in which the value is set on the model instance."""
        statement = ModelFieldAssignmentStatement(
            variable=self.variable.value,
            assigned_value=Argument(value=extractor.extract_value()),
            field_name=extractor.field_name,
        )
        statements.append(statement)

    def get_statements_from_extractors(self, extractors):
        """At the end there has to be a `save` call."""
        statements = super().get_statements_from_extractors(extractors)
        # only add a save statement if any model field was changed
        if len(statements) > 0:
            statements.append(ModelSaveExpression(self.variable.value).as_statement())
        return statements


class FileConverter(ClassConverter):
    """
    This converter can create statements that are used to create files.
    """
    can_use_datatables = True

    def __init__(self, document, related_object, django_project, test_case):
        super().__init__(document, related_object, django_project, test_case)
        self.file = FileProperty(self)
        self.file_variable = NewFileVariableProperty(self)

    def get_document_compatibility(self):
        """Only if a file token was found this converter makes sense."""
        if self.file.token:
            return 1

        return 0

    def get_extractor_class(self, kwarg_representative):
        """All the arguments for `SimpleUploadedFile` are strings. So always return a StringExtractor."""
        return StringExtractor

    def get_extractors(self):
        """There can only be the extractor for the content of the file."""
        locator_file_content = FileContentLocator(self.document)
        locator_file_content.locate()
        fittest_token = locator_file_content.fittest_token

        extractor_instance = self.get_extractor_instance(
            kwarg_representative='content',
            token=fittest_token or 'My content',
        )

        return [extractor_instance]

    def prepare_statements(self, statements):
        statements = super().prepare_statements(statements)
        expression = CreateUploadFileExpression(
            self.file_variable.name or 'foo',
            self.file.locator.file_extension or 'txt',
            None,
        )
        statements.append(AssignmentStatement(variable=self.file_variable.value, expression=expression))
        return statements

    def handle_extractor(self, extractor, statements):
        """The content of the file is extracted. In `prepare_statements` it was set to None. Replace it here."""
        super().handle_extractor(extractor, statements)
        expression = statements[0].expression
        file_content_kwarg = expression.function_kwargs[1]
        file_content_kwarg.value = Argument(extractor.extract_value())


class RequestConverter(ModelConverter):
    """
    This converter is responsible to turn a document into statements that will do a request to the django REST api.
    """
    field_searcher_classes = [SerializerFieldSearcher, ModelFieldSearcher]

    def __init__(self, document, related_object, django_project, test_case):
        super().__init__(document, related_object, django_project, test_case)
        self._url_pattern_adapter = None

        self.user = UserReferenceVariableProperty(self)
        self.model = ModelWithUserProperty(self)
        self.method = MethodProperty(self)
        self.model_variable = ReferenceModelVariableProperty(self)

    def get_searcher_kwargs(self):
        """When searching for a serializer adapter, we need to add the serializer class to the kwargs."""
        kwargs = super().get_searcher_kwargs()
        kwargs['serializer'] = self.url_pattern_adapter.get_serializer_class(self.method.value)()
        return kwargs

    def get_extractor_class(self, kwarg_representative):
        """
        Fields can be represented in two ways in the converter: as a model field (if the rest field does not exist yet)
        or as a rest framework field. Both have different adapters that will result in different extractor
        classes.
        """
        # if the field is referencing the model, use the extractors normally
        if isinstance(kwarg_representative, AbstractModelFieldAdapter):
            return super().get_extractor_class(kwarg_representative)

        # if the field is referencing fields that exist on the serializer, use the extractors that are defined for
        # serializers
        return get_api_model_field_extractor(kwarg_representative)

    def token_used_in_property(self, token):
        if self.method.token == token or self.user.token == token or self.model_variable.token == token:
            return True

        return super().token_used_in_property(token)

    def get_document_compatibility(self):
        """If there is no method, it is unlikely that this converter is useful."""
        if not self.method.token:
            return 0
        return 1

    @property
    def from_anonymous_user(self):
        """Is the request made by an anonymous user? If true there will be no authentication."""
        return isinstance(self.user.token, NoToken)

    @property
    def url_pattern_adapter(self) -> UrlPatternAdapter:
        """
        Returns the url pattern adapter that represents a Django URL pattern that fits the method provided.
        """
        if self._url_pattern_adapter is None:
            searcher = UrlSearcher(str(self.method.token), self.language, self.model.value, [self.method.value])
            self._url_pattern_adapter = searcher.search(self.django_project)
        return self._url_pattern_adapter

    def prepare_statements(self, statements):
        """
        When preparing the statements, there are several things that need to be done before adding the fields.
        """
        if not self.url_pattern_adapter:
            return statements

        # check if there is already a statement with a client that was created
        variable_client = None
        for statement in self.test_case.statements:
            if isinstance(statement.expression, APIClientExpression):
                variable_client = statement.variable

        # if there is no client yet, create one
        if variable_client is None:
            expression_client_init = APIClientExpression()
            variable_client = Variable('client', '')
            statements.append(AssignmentStatement(expression_client_init, variable_client))

        # if the request comes from a user, login with that user
        if not self.from_anonymous_user:
            statements.append(APIClientAuthenticateExpression(variable_client, self.user.value).as_statement())

        # check if a primary key is needed in the request, and if yes collect it from the model variable
        reverse_kwargs = []
        if self.model_variable.token and 'pk' in self.url_pattern_adapter.route_kwargs:
            reverse_kwargs.append(Kwarg('pk', Attribute(self.model_variable.value, 'pk')))

        # create the statement with the request
        expression_request = RequestExpression(
            self.method.value,
            function_kwargs=[],
            reverse_name=self.url_pattern_adapter.reverse_name,
            client_variable=variable_client,
            reverse_kwargs=reverse_kwargs,
        )
        response_variable = Variable('response', '')
        statement_request = AssignmentStatement(expression_request, response_variable)
        statements.append(statement_request)

        return statements

    def handle_extractor(self, extractor, statements):
        """
        Every extractor (for each field) may add values to the request expression/ the data that is sent in the request.
        """
        super().handle_extractor(extractor, statements)

        extracted_value = extractor.extract_value()
        if extracted_value is None:
            return

        # the request is always the last statement that was created in `prepare_statements`
        request_expression = statements[-1].expression
        kwarg = Kwarg(extractor.field_name, extracted_value)

        # some data may be passed via the url or the body, so check if the defined field exists on the url; if yes
        # add it to the reverse expression instead
        if extractor.field_name in self.url_pattern_adapter.route_kwargs:
            kwarg_list = request_expression.reverse_expression.function_kwargs
        else:
            kwarg_list = request_expression.function_kwargs

        kwarg_list.append(kwarg)
