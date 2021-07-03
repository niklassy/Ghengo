from django_meta.api import UrlPatternAdapter
from django_meta.model import AbstractModelAdapter, AbstractModelFieldAdapter
from nlp.converter.base.converter import Converter
from nlp.converter.property import NewModelProperty, NewVariableProperty, ReferenceVariableProperty, \
    ReferenceModelProperty, UserReferenceVariableProperty, ModelWithUserProperty, \
    MethodProperty
from nlp.extractor.fields_rest_api import get_api_model_field_extractor
from nlp.extractor.fields_model import get_model_field_extractor, ModelFieldExtractor
from nlp.generate.argument import Kwarg, Argument
from nlp.generate.attribute import Attribute
from nlp.generate.expression import ModelFactoryExpression, ModelSaveExpression, RequestExpression, APIClientExpression, \
    APIClientAuthenticateExpression
from nlp.generate.statement import AssignmentStatement, ModelFieldAssignmentStatement
from nlp.generate.variable import Variable
from nlp.searcher import ModelFieldSearcher, NoConversionFound, UrlSearcher, SerializerFieldSearcher
from nlp.utils import get_non_stop_tokens, get_noun_chunk_of_token, token_is_noun, get_root_of_token, \
    NoToken


class ModelConverter(Converter):
    field_searcher_classes = [ModelFieldSearcher]

    def __init__(self, document, related_object, django_project, test_case):
        super().__init__(document, related_object, django_project, test_case)
        self._extractors = None
        self._fields = None
        self.model = NewModelProperty(self)
        self.variable = NewVariableProperty(self)

    def get_searcher_kwargs(self):
        return {'model_adapter': self.model.value}

    def _search_for_field(self, span, token):
        """
        Searches for a field with a given span and token inside the self.model_adapter
        """
        for index, searcher_class in enumerate(self.field_searcher_classes):
            no_fallback = index < len(self.field_searcher_classes) - 1
            searcher_kwargs = self.get_searcher_kwargs()

            # all the following nouns will reference fields of that model, so find a field
            if span:
                field_searcher_span = searcher_class(text=str(span), src_language=self.language)

                try:
                    return field_searcher_span.search(raise_exception=True, **searcher_kwargs)
                except NoConversionFound:
                    pass

                field_searcher_root = searcher_class(text=str(span.root.lemma_), src_language=self.language)
                try:
                    return field_searcher_root.search(raise_exception=bool(token), **searcher_kwargs)
                except NoConversionFound:
                    pass

            if token:
                field_searcher_token = searcher_class(text=str(token), src_language=self.language)
                try:
                    return field_searcher_token.search(raise_exception=no_fallback, **searcher_kwargs)
                except NoConversionFound:
                    pass

        return None

    def token_can_be_field(self, token):
        if token == self.model.token or self.variable.token == token:
            return False

        if token.pos_ != 'ADJ' and token.pos_ != 'NOUN' and token.pos_ != 'VERB':
            if token.pos_ != 'PROPN':
                return False

            if self.token_can_be_field(token.head):
                return False

        # verbs with aux are fine (is done, ist abgeschlossen)
        if token.pos_ == 'VERB' and token.head.pos_ != 'AUX':
            return False

        return True

    @property
    def fields(self):
        """Returns all the fields that the document references."""
        if self.model.value is None:
            return []

        if self._fields is None:
            fields = []

            for token in get_non_stop_tokens(self.document):
                if not self.token_can_be_field(token):
                    continue

                chunk = get_noun_chunk_of_token(token, self.document)
                field = self._search_for_field(chunk, token)

                if field in [f for f, _ in fields]:
                    continue

                fields.append((field, token))
            self._fields = fields
        return self._fields

    def get_extractor_class(self, field):
        return get_model_field_extractor(field)

    def get_extractor_kwargs(self, field, field_token, extractor_cls):
        kwargs = {
            'test_case': self.test_case,
            'source': field_token,
            'field': field,
            'document': self.document,
        }

        if issubclass(extractor_cls, ModelFieldExtractor) or extractor_cls == ModelFieldExtractor:
            kwargs['model_adapter'] = self.model.value

        return kwargs

    @property
    def extractors(self):
        """
        Returns all the extractors of this converter. The extractors are responsible to get the values for the fields.
        """
        if len(self.fields) == 0:
            return []

        if self._extractors is None:
            extractors = []

            for field, field_token in self.fields:
                extractor_cls = self.get_extractor_class(field)
                extractors.append(extractor_cls(**self.get_extractor_kwargs(field, field_token, extractor_cls)))

            self._extractors = extractors
        return self._extractors


class ModelFactoryConverter(ModelConverter):
    """
    This converter will convert a document into a model factory statement and everything that belongs to it.
    """
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

    def get_statements_from_datatable(self):
        """
        If a there is a data table on the step, it is assumed that it contains data to create the model entry.
        In that case, use the extractors that already exist and append the ones that are defined in the table.
        """
        statements = []
        datatable = self.related_object.argument
        column_names = datatable.get_column_names()

        for row in datatable.rows:
            extractors_copy = self.extractors.copy()

            for index, cell in enumerate(row.cells):
                field_searcher = ModelFieldSearcher(column_names[index], src_language=self.language)
                field = field_searcher.search(model_adapter=self.model.value)
                extractors_copy.append(
                    ModelFieldExtractor(
                        test_case=self.test_case,
                        model_adapter=self.model.value,
                        field=field,
                        source=cell.value,
                        document=self.document,
                    )
                )

            statements += self.get_statements_from_extractors(extractors_copy)

        return statements


class ModelVariableReferenceConverter(ModelConverter):
    """
    This converter is used in cases where steps simply reference other steps where a variable was defined:
        - Given a user Alice ...
        - And Alice has a password "Haus1234"
    """
    def __init__(self, document, related_object, django_project, test_case):
        super().__init__(document, related_object, django_project, test_case)
        self.variable = ReferenceVariableProperty(self)
        self.model = ReferenceModelProperty(self)

    def get_document_compatibility(self):
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
        statements.append(ModelSaveExpression(self.variable.value).as_statement())
        return statements


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
        self.model_variable = ReferenceVariableProperty(self)

    def get_searcher_kwargs(self):
        kwargs = super().get_searcher_kwargs()
        kwargs['serializer'] = self.url_pattern_adapter.get_serializer_class(self.method.value)()
        return kwargs

    def get_extractor_class(self, field):
        # if the field is referencing the model, use the extractors normally
        if isinstance(field, AbstractModelFieldAdapter):
            return super().get_extractor_class(field)

        # if the field is referencing fields that exist on the serializer, use the extractors that are defined for
        # serializers
        return get_api_model_field_extractor(field)

    def token_can_be_field(self, token):
        if self.method.token == token or self.user.token == token or self.model_variable.token == token:
            return False

        return super().token_can_be_field(token)

    def get_document_compatibility(self):
        if not self.method.token:
            return 0
        return 1

    @property
    def from_anonymous_user(self):
        return isinstance(self.user.token, NoToken)

    @property
    def url_pattern_adapter(self) -> UrlPatternAdapter:
        if self._url_pattern_adapter is None:
            searcher = UrlSearcher(str(self.method.token), self.language, self.model.value, [self.method.value])
            self._url_pattern_adapter = searcher.search(self.django_project)
        return self._url_pattern_adapter

    def prepare_statements(self, statements):
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
