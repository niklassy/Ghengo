from typing import Optional

from django.core.files.uploadedfile import SimpleUploadedFile

from django_meta.api import UrlPatternAdapter
from django_meta.model import AbstractModelFieldAdapter
from nlp.converter.base_converter import Converter
from nlp.converter.property import NewModelProperty, ReferenceModelVariableProperty, \
    ReferenceModelProperty, UserReferenceVariableProperty, ModelWithUserProperty, \
    MethodProperty, FileProperty, NewFileVariableProperty, NewModelVariableProperty, ModelCountProperty
from nlp.converter.wrapper import ConverterInitArgumentWrapper
from nlp.extractor.base import StringExtractor, IntegerExtractor, Extractor
from nlp.extractor.fields_rest_api import get_api_model_field_extractor, ApiModelFieldExtractor
from nlp.extractor.fields_model import get_model_field_extractor, ModelFieldExtractor
from nlp.extractor.output import ModelVariableOutput
from nlp.generate.argument import Kwarg, Argument
from nlp.generate.attribute import Attribute
from nlp.generate.constants import CompareChar
from nlp.generate.expression import ModelFactoryExpression, ModelSaveExpression, RequestExpression, APIClientExpression, \
    APIClientAuthenticateExpression, CreateUploadFileExpression, ModelQuerysetAllExpression, \
    ModelQuerysetFilterExpression, CompareExpression, Expression, FunctionCallExpression
from nlp.generate.index import Index
from nlp.generate.statement import AssignmentStatement, ModelFieldAssignmentStatement, AssertStatement
from nlp.generate.variable import Variable
from nlp.locator import FileExtensionLocator, ComparisonLocator, NounLocator
from nlp.searcher import ModelFieldSearcher, NoConversionFound, UrlSearcher, SerializerFieldSearcher, \
    ClassArgumentSearcher
from nlp.utils import get_non_stop_tokens, get_noun_chunk_of_token, token_is_noun, get_root_of_token, NoToken, \
    token_is_verb


class ClassConverter(Converter):
    """
    This is a base class for any converter that wants to create a class instance.
    """
    field_searcher_classes = []

    def __init__(self, document, related_object, django_project, test_case):
        super().__init__(document, related_object, django_project, test_case)
        self._fields = None
        self._blocked_argument_tokens = []

    def block_token_as_argument(self, token):
        """Use this function to block a specific token from being taken as an argument."""
        if token and token not in self._blocked_argument_tokens:
            self._blocked_argument_tokens.append(token)

    def token_can_be_argument(self, token):
        """Checks if a given token can represent an argument of the __init__ from the class"""
        # first word is always a keyword from Gherkin
        if self.document[0] == token:
            return False

        if any([blocked_token and blocked_token == token for blocked_token in self._blocked_argument_tokens]):
            return False

        if token.pos_ != 'ADJ' and token.pos_ != 'NOUN' and token.pos_ != 'VERB' and token.pos_ != 'ADV':
            if token.pos_ != 'PROPN':
                return False

            if self.token_can_be_argument(token.head):
                return False

        # verbs with aux are fine (is done, ist abgeschlossen)
        if token.pos_ == 'VERB' and token.head.pos_ != 'AUX':
            return False

        last_word = NoToken()
        for i in range(len(self.document)):
            end_token = self.document[-(i + 1)]

            if not end_token.is_punct:
                last_word = end_token
                break

        # if there is a verb where the parent is a finites Modalverb (e.g. sollte), it should not be an argument
        if token == last_word and token_is_verb(token) and token.head.tag_ == 'VMFIN':
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

        if token and str(token) not in search_texts:
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

        self.file = FileProperty(self)
        self.file_variable = NewFileVariableProperty(self)

    def prepare_converter(self):
        self.file_extension_locator.locate()
        # Reject tokens that represent the file, the variable or the extension.
        for t in (self.file.token, self.file_variable.token, self.file_extension_locator.fittest_token):
            self.block_token_as_argument(t)

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

        extracted_value = self.extract_and_handle_output(extractor)

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

    def prepare_converter(self):
        for token in (self.method.token, self.user.token, self.model_variable.token, self.model.token):
            self.block_token_as_argument(token)

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
        field = argument_wrapper.representative.field
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
            url_adapter=self.url_pattern_adapter,
        )
        response_variable = Variable('response', self.url_pattern_adapter.reverse_name)
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
        if extractor.field_name in self.url_pattern_adapter.route_kwargs:
            kwarg_list = request_expression.reverse_expression.function_kwargs
        else:
            kwarg_list = request_expression.function_kwargs

        kwarg_list.append(kwarg)


class QuerysetConverter(ModelConverter):
    """
    This converter can be used to translate text into a queryset statement.
    """
    def get_document_compatibility(self):
        """
        If the model token is not a noun, it is unlikely that this converter matches.
        """
        compatibility = 1

        if not token_is_noun(self.model.token):
            compatibility *= 0.01

        return compatibility

    def prepare_statements(self, statements):
        """
        Create a queryset statement. If there any extractor, filter for it. If there are none, simply get all.
        """
        if len(self.extractors) == 0:
            expression = ModelQuerysetAllExpression(self.model.value)
        else:
            expression = ModelQuerysetFilterExpression(self.model.value, [])

        statement = AssignmentStatement(
            variable=Variable('qs', self.model.value.name),
            expression=expression,
        )
        statements.append(statement)

        return statements

    def handle_extractor(self, extractor, statements):
        super().handle_extractor(extractor, statements)

        qs_statement = statements[0]

        if isinstance(qs_statement.expression, ModelQuerysetAllExpression):
            return

        factory_kwargs = qs_statement.expression.function_kwargs

        extracted_value = self.extract_and_handle_output(extractor)
        kwarg = Kwarg(extractor.field_name, extracted_value)
        factory_kwargs.append(kwarg)


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
        if argument_wrapper.token == self.count.token:
            del kwargs['model_adapter']
            del kwargs['field_adapter']
        return kwargs

    def prepare_converter(self):
        """Block the count token."""
        super().prepare_converter()
        self.block_token_as_argument(self.count.token)

    def get_extractor_class(self, argument_wrapper):
        """
        For everything related to the filter use the normal extractor classes. For the count token use an
        IntegerExtractor instead.
        """
        if argument_wrapper.token == self.count.token:
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
        count_wrapper = ConverterInitArgumentWrapper(
            representative=self.count.value,
            token=self.count.token,
            source_represents_output=True,
        )
        count_extractor = self.get_extractor_instance(count_wrapper)
        count_value = self.extract_and_handle_output(count_extractor)

        # get the comparison value (==, <= etc.)
        compare_locator = ComparisonLocator(self.count.chunk, reverse=False)
        compare_locator.locate()

        # create expression and statement
        expression = CompareExpression(
            Attribute(qs_statement.variable, 'count()'),
            compare_locator.comparison,
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

        statement = AssertStatement(Expression(Attribute(qs_statement.variable, 'exists()')))
        statements.append(statement)

        return statements


class ResponseConverterBase(ClassConverter):
    """
    This is the base class for all converters that relate to the response.
    """
    field_searcher_classes = [SerializerFieldSearcher, ModelFieldSearcher]

    def __init__(self, document, related_object, django_project, test_case):
        super().__init__(document, related_object, django_project, test_case)

        # create some locators that look for certain keywords:
        self.status_locator = NounLocator(self.document, 'status')  # <- status of response
        self.status_locator.locate()

        self.response_locator = NounLocator(self.document, 'response')  # <- response itself
        self.response_locator.locate()

        self.error_locator = NounLocator(self.document, 'error')  # <- response itself
        self.error_locator.locate()

        self.model_in_text = NewModelProperty(self, blocked_tokens=self._blocked_argument_tokens)

    @property
    def model_adapter(self):
        """Returns the model_adapter that is referenced by the variable of the request."""
        referenced_variable = self.get_referenced_response_variable()

        if not referenced_variable:
            return None

        return referenced_variable.value.url_adapter.model_adapter

    @property
    def token_to_extractor_map(self):
        """
        A property that returns a dictionary of:
            token -> extractor

        It can be used to define special extractors for specific tokens. If you want to define any,
        use `get_token_to_extractor_list`. This property is only used to access the values. This is needed because
        some tokens might be NoToken. These instances cannot be used as a key because they have no hash.
        """
        token_extractor_map = {}

        for token, extractor in self.get_token_to_extractor_list():
            if token:
                token_extractor_map[token] = extractor

        return token_extractor_map

    def get_token_to_extractor_list(self):
        """
        Returns a list of tuples (Token, Extractor) to define a specific extractor for a token. This tuple is
        transformed into a dict in `token_to_extractor_map`
        """
        return [
            (self.status_locator.fittest_token, IntegerExtractor),
            (self.error_locator.fittest_token, StringExtractor),
        ]

    def get_extractor_class(self, argument_wrapper: ConverterInitArgumentWrapper):
        """Can use serializer, model fields and the custom extractors."""
        locator_extractor_map = self.token_to_extractor_map

        if argument_wrapper.token and argument_wrapper.token in locator_extractor_map:
            return locator_extractor_map[argument_wrapper.token]

        if isinstance(argument_wrapper.representative, AbstractModelFieldAdapter):
            return get_model_field_extractor(argument_wrapper.representative.field)

        return get_api_model_field_extractor(argument_wrapper.representative.field)

    def get_extractor_kwargs(self, argument_wrapper, extractor_cls):
        """Add the model and the field to the kwargs."""
        kwargs = super().get_extractor_kwargs(argument_wrapper, extractor_cls)

        if extractor_cls == ApiModelFieldExtractor or issubclass(extractor_cls, ApiModelFieldExtractor):
            kwargs['field_adapter'] = argument_wrapper.representative

        # since the class may be for model fields or REST fields, add the model_adapter if needed
        if issubclass(extractor_cls, ModelFieldExtractor) or extractor_cls == ModelFieldExtractor:
            kwargs['model_adapter'] = self.model_adapter
            kwargs['field_adapter'] = argument_wrapper.representative

        return kwargs

    def get_searcher_kwargs(self):
        return {
            'serializer': self.get_referenced_response_variable().value.serializer_class(),
            'model_adapter': self.model_adapter,
        }

    def prepare_converter(self):
        self.block_token_as_argument(self.status_locator.fittest_token)
        self.block_token_as_argument(self.response_locator.fittest_token)

        # only block the model in text if it is actually equal to the one the serializer returns
        model_adapter_from_text = self.model_in_text.value
        if model_adapter_from_text and model_adapter_from_text.models_are_equal(self.model_adapter):
            self.block_token_as_argument(self.model_in_text.token)

    def get_document_compatibility(self):
        compatibility = 1

        # if there is word for response, this converter should be perfect
        if bool(self.response_locator.fittest_token):
            return compatibility

        # if there was no request previously, it is unlikely that this converter is compatible
        if not any([isinstance(s.expression, RequestExpression) for s in self.test_case.statements]):
            compatibility *= 0.1

        return compatibility

    def get_referenced_response_variable(self):
        """
        Returns the variable that holds the request that was previously made.
        """
        valid_variables = []

        for statement in self.test_case.statements:
            if hasattr(statement, 'variable') and isinstance(statement.expression, RequestExpression):
                valid_variables.append(statement.variable)

        if len(valid_variables) == 0:
            return None

        # right now there is no way to determine the exact request that is meant. So just return the last entry
        return valid_variables[-1]

    def extract_and_handle_output(self, extractor):
        extracted_value = super().extract_and_handle_output(extractor)

        # sine we are currently not supporting nested objects, if a model variable is returned from the extractor
        # use the pk instead of that variable
        if extractor.get_output_class() == ModelVariableOutput:
            return Attribute(extracted_value, 'pk')

        return extracted_value


class ResponseStatusCodeConverter(ResponseConverterBase):
    """
    This converter is responsible for checking the status code of a response.
    """
    field_searcher_classes = []

    def get_document_compatibility(self):
        compatibility = super().get_document_compatibility()

        if not self.status_locator.fittest_token:
            compatibility *= 0.2

        return compatibility

    def prepare_statements(self, statements):
        if self.status_locator.fittest_token:
            response_var = self.get_referenced_response_variable()

            wrapper = ConverterInitArgumentWrapper(
                token=self.status_locator.fittest_token,
                representative=self.status_locator.best_compare_value
            )
            extractor = self.get_extractor_instance(wrapper)
            exp = CompareExpression(
                Attribute(response_var, 'status_code'),
                CompareChar.EQUAL,
                self.extract_and_handle_output(extractor),
            )
            statements.append(AssertStatement(expression=exp))

        return statements


class ResponseErrorConverter(ResponseConverterBase):
    """
    This converter is responsible for checking the error message of a response.
    """
    field_searcher_classes = []

    def get_document_compatibility(self):
        compatibility = super().get_document_compatibility()

        if not self.error_locator.fittest_token:
            compatibility *= 0.2

        return compatibility

    def prepare_statements(self, statements):
        if self.error_locator.fittest_token:
            response_var = self.get_referenced_response_variable()

            wrapper = ConverterInitArgumentWrapper(
                token=self.error_locator.fittest_token,
                representative=self.error_locator.best_compare_value
            )
            extractor = self.get_extractor_instance(wrapper)
            exp = CompareExpression(
                Argument(self.extract_and_handle_output(extractor)),
                CompareChar.IN,
                FunctionCallExpression('str', [Attribute(response_var, 'data')]),
            )
            statements.append(AssertStatement(expression=exp))

        return statements


class ResponseConverter(ResponseConverterBase):
    """
    This converter is responsible for text that checks an object that is returned in the response.
    """
    def __init__(self, document, related_object, django_project, test_case):
        super().__init__(document, related_object, django_project, test_case)

        self._response_data_variable = None

    @property
    def response_data_variable(self):
        if self._response_data_variable is None:
            self._response_data_variable = Variable('resp_data', self.model_adapter.name if self.model_adapter else '')
        return self._response_data_variable

    def prepare_statements(self, statements):
        """
        First, save the data field in a separate variable to have easier access later on.
        """
        statements = super().prepare_statements(statements)

        if len(self.extractors) > 0:
            statement = AssignmentStatement(
                variable=self.response_data_variable,
                expression=Expression(Attribute(self.get_referenced_response_variable(), 'data')),
            )
            statements.append(statement)

        return statements

    def handle_extractor(self, extractor, statements):
        """
        For each extractor create an assert statement and check for the value.
        """
        super().handle_extractor(extractor, statements)

        chunk = get_noun_chunk_of_token(extractor.source, self.document)
        compare_locator = ComparisonLocator(chunk or self.document, reverse=False)
        compare_locator.locate()

        assert_statement = AssertStatement(
            CompareExpression(
                # variable.get()
                FunctionCallExpression(
                    Attribute(self.response_data_variable, 'get'),
                    [Argument(extractor.field_name)],
                ),
                # ==
                compare_locator.comparison,
                # value
                Argument(self.extract_and_handle_output(extractor)),
            )
        )
        statements.append(assert_statement)


class ManyResponseConverter(ResponseConverterBase):
    """
    This converter is a base class for response that return a list instead of a simple object.
    """
    def __init__(self, document, related_object, django_project, test_case):
        super().__init__(document, related_object, django_project, test_case)

        # keywords to identify a list:
        self.response_list_locator = NounLocator(self.document, 'list')
        self.response_list_locator.locate()

        self.response_length_locator = NounLocator(self.document, 'length')
        self.response_length_locator.locate()

        self.response_entry_locator = NounLocator(self.document, 'entry')
        self.response_entry_locator.locate()

    def prepare_converter(self):
        self.block_token_as_argument(self.response_list_locator.fittest_token)
        self.block_token_as_argument(self.response_length_locator.fittest_token)
        self.block_token_as_argument(self.response_entry_locator.fittest_token)
        # keep this at the end
        super().prepare_converter()

    def get_token_to_extractor_list(self):
        token_locator_list = super().get_token_to_extractor_list()

        token_locator_list.append((self.response_length_locator.fittest_token, IntegerExtractor))
        token_locator_list.append((self.response_entry_locator.fittest_token, IntegerExtractor))

        return token_locator_list

    def get_document_compatibility(self):
        compatibility = super().get_document_compatibility()

        # if a list is mentioned, the response will most likely be a list
        list_token = self.response_list_locator.fittest_token

        # if the length of the response is checked, most likely multiple objects are returned
        length_token = self.response_length_locator.fittest_token

        # if there is the word `entry` it is likely that multiple objects are returned
        entry_token = self.response_entry_locator.fittest_token

        if not list_token and not length_token and not entry_token:
            compatibility *= 0.3

        # make sure to stay between 0 and 1
        return compatibility


class ManyCheckEntryResponseConverter(ManyResponseConverter):
    """
    This converter can be used to check specific entries in a given list from the response.
    """
    def __init__(self, document, related_object, django_project, test_case):
        super().__init__(document, related_object, django_project, test_case)

        if self.get_entry_extractor() is not None:
            extractor = self.get_entry_extractor()
            extracted_value = extractor.extract_value()

            # if there is a warning set number to 1 to get the first entry
            if not extractor.generates_warning:
                index = extracted_value - 1
            else:
                index = extracted_value

            # use the index
            self.entry_variable = Variable('entry_{}'.format(index), self.model_adapter)
        else:
            self.entry_variable = None

    def get_entry_extractor(self) -> Optional[Extractor]:
        """
        Return the extractor that is responsible for getting the index of the entry.
        """
        source = self.response_entry_locator.fittest_token

        if not source:
            return None

        wrapper = ConverterInitArgumentWrapper(token=source, representative=source)
        return self.get_extractor_instance(wrapper)

    def get_document_compatibility(self):
        compatibility = super().get_document_compatibility()

        entry_extractor = self.get_entry_extractor()

        # if there is no extractor for the entry, we cannot determine which entry we should check
        if entry_extractor is None:
            compatibility *= 0.1
            return compatibility

        entry_token = self.response_entry_locator.fittest_token
        output_source = entry_extractor.output.output_source

        # since we are referring to the first or second or third entry, those words should be adjectives
        # when checking the length, direct numbers are used instead (e.g. two entries)
        if not entry_token or (output_source and output_source.pos_ != 'ADJ'):
            compatibility *= 0.2

        return compatibility

    def prepare_statements(self, statements):
        """
        To prepare the statements, create an assignment statement that will hold the referenced entry of the list.
        """
        number_extractor = self.get_entry_extractor()
        if number_extractor is None:
            return

        # extracted value might be a GenerationWarning
        extracted_number = self.extract_and_handle_output(number_extractor)

        # if there is no warning, subtract 1 since we need to translate to index values
        if not number_extractor.generates_warning:
            extracted_number = extracted_number - 1

        statement = AssignmentStatement(
            variable=self.entry_variable,
            expression=Expression(
                Index(Attribute(self.get_referenced_response_variable(), 'data'), extracted_number)
            )
        )

        statements.append(statement)

        return statements

    def handle_extractor(self, extractor, statements):
        """
        For each extractor, create an assert statement and compare the value of the previously created variable
        via `get` and the desired value that is extracted.
        """
        statement = AssertStatement(
            CompareExpression(
                FunctionCallExpression(
                    Attribute(self.entry_variable, 'get'),
                    [Argument(extractor.field_name)],
                ),
                CompareChar.EQUAL,
                Argument(self.extract_and_handle_output(extractor)),
            )
        )

        statements.append(statement)


class ManyLengthResponseConverter(ManyResponseConverter):
    """
    This converter is used for cases where the length of the response is detected and turned into statements.
    """
    field_searcher_classes = []

    def get_token_to_extractor_list(self):
        token_extractor_list = super().get_token_to_extractor_list()
        token_extractor_list.append((self.get_length_token(), IntegerExtractor))
        return token_extractor_list

    def get_length_token(self):
        """
        Returns the token that represents the length of the response.
        """
        fittest_token = self.response_length_locator.fittest_token or self.response_entry_locator.fittest_token

        if fittest_token:
            return fittest_token

        return self.model_in_text.token

    def get_length_extractor(self):
        """
        Returns the extractor of the length token.
        """
        token = self.get_length_token()

        if not token:
            return None

        wrapper = ConverterInitArgumentWrapper(token=token, representative=token)
        return self.get_extractor_instance(wrapper)

    def get_document_compatibility(self):
        compatibility = super().get_document_compatibility()

        # if there is no length extractor, this does not fit
        length_extractor = self.get_length_extractor()
        if not length_extractor:
            return 0

        # if an integer value is returned, it is very likely that this converter fits
        if not isinstance(length_extractor.extract_value(), int):
            compatibility *= 0.5

        return compatibility

    def prepare_statements(self, statements):
        statements = super().prepare_statements(statements)

        chunk = get_noun_chunk_of_token(self.get_length_token(), self.document)
        compare_locator = ComparisonLocator(chunk or self.document, reverse=False)
        compare_locator.locate()

        length_extractor = self.get_length_extractor()

        if not length_extractor:
            return statements

        exp = CompareExpression(
            FunctionCallExpression('len', [Attribute(self.get_referenced_response_variable(), 'data')]),
            compare_locator.comparison,
            Argument(self.extract_and_handle_output(length_extractor)),
        )
        statements.append(AssertStatement(exp))

        return statements
