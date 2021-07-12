from django.core.files.uploadedfile import SimpleUploadedFile

from django_meta.api import UrlPatternAdapter
from django_meta.model import AbstractModelAdapter, AbstractModelFieldAdapter
from nlp.converter.base_converter import Converter
from nlp.converter.property import NewModelProperty, ReferenceModelVariableProperty, \
    ReferenceModelProperty, UserReferenceVariableProperty, ModelWithUserProperty, \
    MethodProperty, FileProperty, NewFileVariableProperty, NewModelVariableProperty
from nlp.converter.wrapper import ConverterInitArgumentWrapper
from nlp.extractor.base import StringExtractor
from nlp.extractor.fields_rest_api import get_api_model_field_extractor
from nlp.extractor.fields_model import get_model_field_extractor, ModelFieldExtractor
from nlp.generate.argument import Kwarg, Argument
from nlp.generate.attribute import Attribute
from nlp.generate.expression import ModelFactoryExpression, ModelSaveExpression, RequestExpression, APIClientExpression, \
    APIClientAuthenticateExpression, CreateUploadFileExpression
from nlp.generate.statement import AssignmentStatement, ModelFieldAssignmentStatement
from nlp.generate.variable import Variable
from nlp.locator import FileExtensionLocator
from nlp.searcher import ModelFieldSearcher, NoConversionFound, UrlSearcher, SerializerFieldSearcher, \
    ClassArgumentSearcher
from nlp.utils import get_non_stop_tokens, get_noun_chunk_of_token, token_is_noun, get_root_of_token, \
    NoToken


class ClassConverter(Converter):
    """
    This is a base class for any converter that wants to create a class instance.
    """
    field_searcher_classes = []

    def __init__(self, document, related_object, django_project, test_case):
        super().__init__(document, related_object, django_project, test_case)
        self._fields = None

    def token_used_in_property(self, token):
        """Is this token used in a ConverterProperty?"""
        return False

    def token_can_be_argument(self, token):
        """Checks if a given token can represent an argument of the __init__ from the class"""
        # first word is always a keyword from Gherkin
        if self.document[0] == token:
            return False

        if self.token_used_in_property(token):
            return False

        if token.pos_ != 'ADJ' and token.pos_ != 'NOUN' and token.pos_ != 'VERB' and token.pos_ != 'ADV':
            if token.pos_ != 'PROPN':
                return False

            if self.token_can_be_argument(token.head):
                return False

        # verbs with aux are fine (is done, ist abgeschlossen)
        if token.pos_ == 'VERB' and token.head.pos_ != 'AUX':
            return False

        return True

    def get_searcher_kwargs(self):
        """Returns the kwargs that are passed to the `search` method from a searcher."""
        return {}

    def search_for_init_argument(self, span, token):
        """
        This method will use searcher to search for an argument of the class. It will observe the span and
        the token and will return whatever the searcher returns.
        """
        searcher_kwargs = self.get_searcher_kwargs()

        search_texts = []
        if span:
            search_texts += [str(span), str(span.root.lemma_)]

        if token:
            search_texts.append(str(token))

        for index, searcher_class in enumerate(self.field_searcher_classes):
            last_searcher_class = index == len(self.field_searcher_classes) - 1

            for search_text_index, search_text in enumerate(search_texts):
                searcher = searcher_class(search_text, src_language=self.language)

                # only raise no exception if it is the last searcher class and the last text to have a fallback
                last_search_text = search_text_index == len(search_texts) - 1
                raise_exception = not last_search_text or not last_searcher_class

                try:
                    return searcher.search(**searcher_kwargs, raise_exception=raise_exception)
                except NoConversionFound:
                    pass

        return None

    def is_valid_search_result(self, search_result):
        """This method can be used to filter out specific search results before they are turned into extractors."""
        return bool(search_result)

    def get_default_argument_wrappers(self) -> [ConverterInitArgumentWrapper]:
        """Returns a list of default arguments wrappers. For each the selected value will be forced."""
        return []

    def get_argument_wrappers(self) -> [ConverterInitArgumentWrapper]:
        """
        Returns a list of objects that hold a token and the representative for an argument of the __init__ for the
        class. These objects are used to create extractors.
        """
        default_argument_wrappers = self.get_default_argument_wrappers()
        argument_wrappers = []

        for token in get_non_stop_tokens(self.document):
            if not self.token_can_be_argument(token):
                continue

            chunk = get_noun_chunk_of_token(token, self.document)
            representative = self.search_for_init_argument(chunk, token)

            # if the result is not valid, skip it
            if not self.is_valid_search_result(representative):
                continue

            # if the representative is already present, skip it
            if representative in [wrapper.representative for wrapper in argument_wrappers]:
                continue

            wrapper = ConverterInitArgumentWrapper(representative=representative, token=token)
            argument_wrappers.append(wrapper)

        # add default values if needed
        wrapper_identifiers = [wrapper.identifier for wrapper in argument_wrappers]
        for default_wrapper in default_argument_wrappers:
            if default_wrapper.identifier not in wrapper_identifiers:
                # force the result of the defaults
                default_wrapper.source_represents_output = True
                argument_wrappers.append(default_wrapper)

        return argument_wrappers

    def get_extractor_class(self, argument_wrapper: ConverterInitArgumentWrapper):
        """This returns the extractor class based on the ConverterInitArgumentWrapper."""
        raise NotImplementedError()

    def get_extractor_kwargs(self, argument_wrapper: ConverterInitArgumentWrapper, extractor_cls):
        """Returns the kwargs that are passed to the extractor to instanciate it."""
        return {
            'test_case': self.test_case,
            'source': argument_wrapper.token,
            'document': self.document,
            'representative': argument_wrapper.representative,
        }

    def get_extractor_instance(self, argument_wrapper: ConverterInitArgumentWrapper):
        """Returns an instance of an extractor for a given argument wrapper."""
        extractor_class = self.get_extractor_class(argument_wrapper=argument_wrapper)
        kwargs = self.get_extractor_kwargs(
            argument_wrapper=argument_wrapper,
            extractor_cls=extractor_class,
        )

        instance = extractor_class(**kwargs)
        if argument_wrapper.source_represents_output:
            instance.source_represents_output = True
        return instance

    def get_extractors(self):
        """Returns the extractors for this converter."""
        wrappers = self.get_argument_wrappers()

        return [self.get_extractor_instance(argument_wrapper=wrapper) for wrapper in wrappers]

    def get_statements_from_datatable(self):
        """
        Handles if the passed Step has a data table. It will get the normal extractors and append any values that
        are passed by the data table. The extractors are added to the existing list. For each row of the
        data table the statements are created again.
        """
        statements = []
        datatable = self.related_object.argument
        column_names = datatable.get_column_names()

        for row in datatable.rows:
            extractors_copy = self.extractors.copy()

            for index, cell in enumerate(row.cells):
                representative = self.search_for_init_argument(span=None, token=column_names[index])

                # filter any invalid search results
                if not self.is_valid_search_result(representative):
                    continue

                wrapper = ConverterInitArgumentWrapper(token=cell.value, representative=representative)
                extractor_instance = self.get_extractor_instance(argument_wrapper=wrapper)

                existing_extract_index = -1
                for extractor_index, extractor in enumerate(extractors_copy):
                    if extractor.representative == representative:
                        existing_extract_index = extractor_index
                        break

                if existing_extract_index >= 0:
                    extractors_copy[existing_extract_index] = extractor_instance
                else:
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

    def get_extractor_class(self, argument_wrapper):
        """The extractor class needs to be determined based on the kwarg_representative which is a model field."""
        return get_model_field_extractor(argument_wrapper.representative)

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

        if not self.model.value.model_exists_in_code:
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
    field_searcher_classes = [ClassArgumentSearcher]

    class ArgumentRepresentatives:
        """The names for the arguments from SimpleUploadedFile"""
        CONTENT = 'content'
        NAME = 'name'

        @classmethod
        def get_all(cls):
            return [cls.CONTENT, cls.NAME]

    def __init__(self, document, related_object, django_project, test_case):
        super().__init__(document, related_object, django_project, test_case)
        # get the extension of the file
        self.file_extension_locator = FileExtensionLocator(self.document)
        self.file_extension_locator.locate()

        self.file = FileProperty(self)
        self.file_variable = NewFileVariableProperty(self)

    def token_used_in_property(self, token):
        """Reject tokens that represent the file, the variable or the extension."""
        return any([
            self.file.token == token,
            self.file_variable.token == token,
            self.file_extension_locator.fittest_token == token,
        ])

    def get_document_compatibility(self):
        """Only if a file token was found this converter makes sense."""
        if self.file.token:
            return 1

        return 0

    def get_extractor_class(self, argument_wrapper):
        """All the arguments for `SimpleUploadedFile` are strings. So always return a StringExtractor."""
        return StringExtractor

    def get_searcher_kwargs(self):
        """We are searching for the parameters of the init from SimpleUploadFile but want to exclude content_type."""
        return {'cls': SimpleUploadedFile, 'exclude_parameters': ['content_type']}

    def is_valid_search_result(self, search_result):
        """Only allow name and content."""
        if not super().is_valid_search_result(search_result):
            return False

        return search_result in self.ArgumentRepresentatives.get_all()

    def get_default_argument_wrappers(self) -> [ConverterInitArgumentWrapper]:
        """
        Add some defaults values since content and name are required to create a file. `source_represents_output` is
        set by the parent.
        """
        return [
            ConverterInitArgumentWrapper(
                token='My content', representative=self.ArgumentRepresentatives.CONTENT),
            ConverterInitArgumentWrapper(
                token=self.file_variable.token or 'foo', representative=self.ArgumentRepresentatives.NAME)
        ]

    def prepare_statements(self, statements):
        """Create the statement for the file."""
        statements = super().prepare_statements(statements)
        expression = CreateUploadFileExpression([])
        statements.append(AssignmentStatement(variable=self.file_variable.value, expression=expression))
        return statements

    def handle_extractor(self, extractor, statements):
        """The content of the file is extracted. In `prepare_statements` it was set to None. Replace it here."""
        super().handle_extractor(extractor, statements)
        expression = statements[0].expression

        extracted_value = extractor.extract_value()
        if extracted_value is None:
            return

        # get the representative which should be name or content
        representative = extractor.representative
        # ignore GenerationWarnings
        if representative == self.ArgumentRepresentatives.NAME and not extractor.generates_warning:
            # add the file extension to the extracted value
            extracted_value = '{}.{}'.format(extracted_value, self.file_extension_locator.best_compare_value or 'txt')

        kwarg = Kwarg(representative, extracted_value)
        expression.add_kwarg(kwarg)


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

    def token_used_in_property(self, token):
        return any([
            self.method.token == token,
            self.user.token == token,
            self.model_variable.token == token,
            self.model.token == token,
        ])

    def get_searcher_kwargs(self):
        """When searching for a serializer adapter, we need to add the serializer class to the kwargs."""
        serializer = None

        if self.url_pattern_adapter:
            serializer = self.url_pattern_adapter.get_serializer_class(self.method.value)()

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
        field = argument_wrapper.representative
        if isinstance(field, AbstractModelFieldAdapter):
            return super().get_extractor_class(argument_wrapper)

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
