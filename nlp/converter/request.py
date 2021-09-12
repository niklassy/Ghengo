from django_meta.api import UrlPatternWrapper
from django_meta.model import AbstractModelFieldWrapper
from nlp.converter.base.converter import ClassConverter
from nlp.converter.property import UserReferenceVariableProperty, MethodProperty, \
    ReferenceModelVariableProperty, NewModelProperty
from nlp.extractor.fields_model import get_model_field_extractor, ModelFieldExtractor
from nlp.extractor.fields_rest_api import get_api_model_field_extractor
from nlp.generate.argument import Kwarg
from nlp.generate.attribute import Attribute
from nlp.generate.expression import RequestExpression, APIClientAuthenticateExpression, APIClientExpression
from nlp.generate.statement import AssignmentStatement
from nlp.generate.variable import Variable
from nlp.lookout.project import SerializerFieldLookout, ModelFieldLookout, UrlLookout
from nlp.utils import tokens_are_equal, NoToken


class RequestConverter(ClassConverter):
    """
    This converter is responsible to turn a document into statements that will do a request to the django REST api.
    """
    field_lookout_classes = [SerializerFieldLookout, ModelFieldLookout]

    def __init__(self, document, related_object, django_project, test_case):
        super().__init__(document, related_object, django_project, test_case)
        self._url_pattern_wrapper = None

        self.user = UserReferenceVariableProperty(self)
        self.method = MethodProperty(self)

        # the new model property should not contain the user information, if there is any
        blocked_model_tokens = [self.method.token]
        if self.user.token:
            blocked_model_tokens += [self.user.chunk.root, self.user.token]
        self.model = NewModelProperty(self, blocked_tokens=blocked_model_tokens)

        self.model_variable = ReferenceModelVariableProperty(self)

    def get_document_verbs(self):
        return [t for t in self.get_possible_argument_tokens() if t.pos_ == 'VERB']

    def token_can_be_argument(self, token):
        can_be_argument = super().token_can_be_argument(token)
        if not can_be_argument:
            return False

        # when making a request the last verb typically describes the action (get, geholt, holen, bekommen, erstellen)
        # this can be covered by the method token, but the method is not always determined by the verb
        if token.pos_ == 'VERB':
            all_verbs = self.get_document_verbs()

            if len(all_verbs) > 0 and all_verbs[-1] == token:
                return False

        return True

    def prepare_converter(self):
        for token in (self.method.token, self.user.token, self.model_variable.token, self.model.token):
            self.block_token_as_argument(token)

        # if there is a user token, it might be defined as "Alice" or "User 1", if there is a token we also want
        # to block the root which would be `User` in the second example
        if self.user.token:
            self.block_token_as_argument(self.user.chunk.root)

    def get_lookout_kwargs(self):
        """When searching for a serializer wrapper, we need to add the serializer class to the kwargs."""
        serializer = None

        if self.url_pattern_wrapper:
            serializer_class = self.url_pattern_wrapper.get_serializer_class(self.method.value)

            if serializer_class:
                serializer = self.url_pattern_wrapper.get_serializer_class(self.method.value)()
            else:
                serializer = None

        return {
            'serializer': serializer,
            'model_wrapper': self.model.value,
        }

    def get_extractor_kwargs(self, argument_wrapper, extractor_cls):
        kwargs = super().get_extractor_kwargs(argument_wrapper, extractor_cls)
        kwargs['field_wrapper'] = argument_wrapper.representative

        # since the class may be for model fields or REST fields, add the model_wrapper if needed
        if issubclass(extractor_cls, ModelFieldExtractor) or extractor_cls == ModelFieldExtractor:
            kwargs['model_wrapper'] = self.model.value

        return kwargs

    def get_extractor_class(self, argument_wrapper):
        """
        Fields can be represented in two ways in the converter: as a model field (if the rest field does not exist yet)
        or as a rest framework field. Both have different wrappers that will result in different extractor
        classes.
        """
        # if the field is referencing the model, use the extractors normally
        field = argument_wrapper.representative.field
        if isinstance(argument_wrapper.representative, AbstractModelFieldWrapper):
            return get_model_field_extractor(field)

        # if the field is referencing fields that exist on the serializer, use the extractors that are defined for
        # serializers
        return get_api_model_field_extractor(field)

    def get_document_compatibility(self):
        """
        For now there are not many alternatives for a request converter, if there are any new, this has to be
        refactored
        """
        if not self.url_pattern_wrapper:
            return 0
        return 1

    @property
    def from_anonymous_user(self):
        """Is the request made by an anonymous user? If true there will be no authentication."""
        return not bool(self.user.token)

    @property
    def url_pattern_wrapper(self) -> UrlPatternWrapper:
        """
        Returns the url pattern wrapper that represents a Django URL pattern that fits the method provided.
        """
        if self._url_pattern_wrapper is None:
            all_verbs = self.get_document_verbs()
            try:
                last_verb = all_verbs[-1]
            except IndexError:
                last_verb = NoToken()

            lookout = UrlLookout(
                # use either the method or the verb to determine the url
                text=str(self.method.token or last_verb),
                language=self.language,
                model_wrapper=self.model.value,
                valid_methods=[self.method.value] if self.method.value else [],
            )
            self._url_pattern_wrapper = lookout.locate(self.django_project)
        return self._url_pattern_wrapper

    def extract_method(self):
        """
        Returns the method for the statements. This also has the fallback for the cases where the text
        has no obvious hint about the method. It will use the url pattern wrapper instead.
        """
        try:
            fallback_method = self.url_pattern_wrapper.methods[0]
        except IndexError:
            fallback_method = 'get'

        return self.method.value or fallback_method

    def prepare_statements(self, statements):
        """
        When preparing the statements, there are several things that need to be done before adding the fields.
        """
        if not self.url_pattern_wrapper:
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
            statements.append(
                APIClientAuthenticateExpression(variable_client.get_reference(), self.user.value).as_statement()
            )

        # check if a primary key is needed in the request, and if yes collect it from the model variable
        reverse_kwargs = []
        model_token = self.model_variable.token
        user_token = self.user.token
        pk_in_route_kwargs = self.url_pattern_wrapper.key_exists_in_route_kwargs('pk')

        if model_token and not tokens_are_equal(model_token, user_token) and pk_in_route_kwargs:
            reverse_kwargs.append(Kwarg('pk', Attribute(self.model_variable.value, 'pk')))

        # create the statement with the request
        expression_request = RequestExpression(
            self.extract_method(),
            function_kwargs=[],
            reverse_name=self.url_pattern_wrapper.reverse_name,
            client_variable=variable_client.get_reference(),
            reverse_kwargs=reverse_kwargs,
            url_wrapper=self.url_pattern_wrapper,
        )

        # get the variable name by checking how many other request expressions already exist
        other_request_expressions = self.test_case.get_all_statements_with_expression(RequestExpression)

        if len(other_request_expressions) == 0:
            variable_name = 'response'
        else:
            variable_name = 'response_{}'.format(len(other_request_expressions))

        response_variable = Variable(variable_name, self.url_pattern_wrapper.reverse_name)
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

        kwargs_for_url = request_expression.reverse_expression.function_kwargs
        kwarg_for_body = request_expression.function_kwargs

        # some data may be passed via the url or the body, so check if the defined field exists on the url; if yes
        # add it to the reverse expression instead
        if self.url_pattern_wrapper.key_exists_in_route_kwargs(extractor.field_name):
            kwarg_list = kwargs_for_url
        else:
            kwarg_list = kwarg_for_body

        kwarg_list.append(kwarg)
