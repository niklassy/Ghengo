from django_meta.api import UrlPatternAdapter
from django_meta.model import AbstractModelFieldAdapter
from nlp.converter.base.converter import ClassConverter
from nlp.converter.property import UserReferenceVariableProperty, ModelWithUserProperty, MethodProperty, \
    ReferenceModelVariableProperty
from nlp.extractor.fields_model import get_model_field_extractor, ModelFieldExtractor
from nlp.extractor.fields_rest_api import get_api_model_field_extractor
from nlp.generate.argument import Kwarg
from nlp.generate.attribute import Attribute
from nlp.generate.expression import RequestExpression, APIClientAuthenticateExpression, APIClientExpression
from nlp.generate.statement import AssignmentStatement
from nlp.generate.variable import Variable
from nlp.searcher import UrlSearcher, SerializerFieldSearcher, ModelFieldSearcher


class RequestConverter(ClassConverter):
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

    def prepare_converter(self):
        for token in (self.method.token, self.user.token, self.model_variable.token, self.model.token):
            self.block_token_as_argument(token)

    def get_searcher_kwargs(self):
        """When searching for a serializer adapter, we need to add the serializer class to the kwargs."""
        serializer = None

        if self.url_pattern_adapter:
            serializer_class = self.url_pattern_adapter.get_serializer_class(self.method.value)

            if serializer_class:
                serializer = self.url_pattern_adapter.get_serializer_class(self.method.value)()
            else:
                serializer = None

        return {
            'serializer': serializer,
            'model_adapter': self.model.value,
        }

    def get_extractor_kwargs(self, argument_wrapper, extractor_cls):
        kwargs = super().get_extractor_kwargs(argument_wrapper, extractor_cls)
        kwargs['field_adapter'] = argument_wrapper.representative

        # since the class may be for model fields or REST fields, add the model_adapter if needed
        if issubclass(extractor_cls, ModelFieldExtractor) or extractor_cls == ModelFieldExtractor:
            kwargs['model_adapter'] = self.model.value

        return kwargs

    def get_extractor_class(self, argument_wrapper):
        """
        Fields can be represented in two ways in the converter: as a model field (if the rest field does not exist yet)
        or as a rest framework field. Both have different adapters that will result in different extractor
        classes.
        """
        # if the field is referencing the model, use the extractors normally
        field = argument_wrapper.representative.field
        if isinstance(argument_wrapper.representative, AbstractModelFieldAdapter):
            return get_model_field_extractor(field)

        # if the field is referencing fields that exist on the serializer, use the extractors that are defined for
        # serializers
        return get_api_model_field_extractor(field)

    def get_document_compatibility(self):
        """If there is no method, it is unlikely that this converter is useful."""
        if not self.method.token or not self.url_pattern_adapter:
            return 0
        return 1

    @property
    def from_anonymous_user(self):
        """Is the request made by an anonymous user? If true there will be no authentication."""
        return not bool(self.user.token)

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
        model_token = self.model_variable.token
        user_token = self.user.token

        if model_token and model_token != user_token and self.url_pattern_adapter.key_exists_in_route_kwargs('pk'):
            reverse_kwargs.append(Kwarg('pk', Attribute(self.model_variable.value, 'pk')))

        # create the statement with the request
        expression_request = RequestExpression(
            self.method.value,
            function_kwargs=[],
            reverse_name=self.url_pattern_adapter.reverse_name,
            client_variable=variable_client,
            reverse_kwargs=reverse_kwargs,
            url_adapter=self.url_pattern_adapter,
        )

        # get the variable name by checking how many other request expressions already exist
        other_request_expressions = [
            s for s in self.test_case.statements if isinstance(s.expression, RequestExpression)
        ]

        if len(other_request_expressions) == 0:
            variable_name = 'response'
        else:
            variable_name = 'response_{}'.format(len(other_request_expressions))

        response_variable = Variable(variable_name, self.url_pattern_adapter.reverse_name)
        statement_request = AssignmentStatement(expression_request, response_variable)
        statements.append(statement_request)

        return statements

    def handle_extractor(self, extractor, statements):
        """
        Every extractor (for each field) may add values to the request expression/ the data that is sent in the request.
        """
        super().handle_extractor(extractor, statements)

        extracted_value = self.extract_and_handle_output(extractor)

        # the request is always the last statement that was created in `prepare_statements`
        request_expression = statements[-1].expression
        kwarg = Kwarg(extractor.field_name, extracted_value)

        # some data may be passed via the url or the body, so check if the defined field exists on the url; if yes
        # add it to the reverse expression instead
        if self.url_pattern_adapter.key_exists_in_route_kwargs(extractor.field_name):
            kwarg_list = request_expression.reverse_expression.function_kwargs
        else:
            kwarg_list = request_expression.function_kwargs

        kwarg_list.append(kwarg)
