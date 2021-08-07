from typing import Optional

from django_meta.model import AbstractModelFieldAdapter
from nlp.converter.base.converter import ClassConverter
from nlp.converter.property import NewModelProperty
from nlp.converter.wrapper import ConverterInitArgumentWrapper
from nlp.extractor.base import IntegerExtractor, Extractor, StringExtractor
from nlp.extractor.fields_model import ModelFieldExtractor, get_model_field_extractor
from nlp.extractor.fields_rest_api import ApiModelFieldExtractor, get_api_model_field_extractor
from nlp.extractor.output import ModelVariableOutput
from nlp.generate.argument import Argument
from nlp.generate.attribute import Attribute
from nlp.generate.constants import CompareChar
from nlp.generate.expression import CompareExpression, FunctionCallExpression, Expression, RequestExpression
from nlp.generate.index import Index
from nlp.generate.statement import AssertStatement, AssignmentStatement
from nlp.generate.variable import Variable
from nlp.locator import ComparisonLocator, NounLocator
from nlp.searcher import SerializerFieldSearcher, ModelFieldSearcher
from nlp.utils import get_noun_chunk_of_token, NoToken


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

        self.error_locator = NounLocator(self.document, 'error')  # <- error
        self.error_locator.locate()

        self.model_in_text = NewModelProperty(self, blocked_tokens=self._blocked_argument_tokens)

    @property
    def model_adapter_from_request(self):
        """Returns the model_adapter that is referenced by the variable of the request."""
        referenced_variable = self.get_referenced_response_variable()

        if not referenced_variable:
            return None

        return referenced_variable.value.url_adapter.model_adapter

    @property
    def model_in_text_fits_request(self):
        """Checks if the model in the text is valid and fits to the one provided by the request."""
        model_adapter = self.model_adapter_from_request

        if not model_adapter:
            return False

        return model_adapter.models_are_equal(self.model_in_text.value)

    @property
    def _token_to_extractor_map(self):
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
        transformed into a dict in `_token_to_extractor_map`
        """
        return [
            (self.status_locator.fittest_token, IntegerExtractor),
            (self.error_locator.fittest_token, StringExtractor),
        ]

    def get_extractor_class(self, argument_wrapper: ConverterInitArgumentWrapper):
        """Can use serializer, model fields and the custom extractors."""
        locator_extractor_map = self._token_to_extractor_map

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
            kwargs['model_adapter'] = self.model_adapter_from_request
            kwargs['field_adapter'] = argument_wrapper.representative

        return kwargs

    def get_searcher_kwargs(self):
        serializer_class = self.get_referenced_response_variable().value.serializer_class

        return {
            'serializer': serializer_class() if serializer_class else None,
            'model_adapter': self.model_adapter_from_request,
        }

    def prepare_converter(self):
        self.block_token_as_argument(self.status_locator.fittest_token)
        self.block_token_as_argument(self.response_locator.fittest_token)

        # only block the model in text if it is actually equal to the one the serializer returns
        if self.model_in_text_fits_request:
            self.block_token_as_argument(self.model_in_text.token)

    def get_document_compatibility(self):
        compatibility = 1

        # if there was no request previously, it is unlikely that this converter is compatible
        if not any([isinstance(s.expression, RequestExpression) for s in self.test_case.statements]):
            compatibility *= 0.1

        return compatibility

    def get_referenced_response_variable(self) -> Optional[Variable]:
        """
        Returns the variable that holds the request that was previously made and that is referenced here.
        """
        valid_variables = []

        # first get all variables that hold an expression for a request
        for statement in self.test_case.statements:
            if hasattr(statement, 'variable') and isinstance(statement.expression, RequestExpression):
                valid_variables.append(statement.variable)

        if len(valid_variables) == 0:
            return None

        # there is the option that a specific request was referenced (e.g. `the first response`), if not simply return
        # the last entry
        if not self.response_locator.fittest_token:
            return valid_variables[-1]

        wrapper = ConverterInitArgumentWrapper(
            representative=self.response_locator.best_compare_value,
            token=self.response_locator.fittest_token,
        )

        # always get the integer for the response -> which response is meant?
        response_extractor = self.get_extractor_instance(wrapper, IntegerExtractor)
        if response_extractor.generates_warning:
            return valid_variables[-1]

        # if the return value is fine, extract the number and try to access it from all the variables
        response_number = response_extractor.extract_value()
        try:
            return valid_variables[response_number - 1]
        except IndexError:
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
                Argument(self.extract_and_handle_output(extractor)),
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

    def get_document_compatibility(self):
        compatibility = super().get_document_compatibility()

        # if the response is not explicitly named
        if not self.response_locator.fittest_token:

            # check if there is a model in the text, if not it is very unlikely to fit
            if self.model_in_text.token:

                # if there is a model token and it fits the request model, this is likely to fit though
                if self.model_in_text_fits_request:
                    compatibility *= 1
                else:
                    compatibility *= 0.5
            else:
                compatibility *= 0.2

        return compatibility

    @property
    def response_data_variable(self):
        if self._response_data_variable is None:
            self._response_data_variable = Variable(
                'resp_data',
                self.model_adapter_from_request.name if self.model_adapter_from_request else '',
            )
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
        extracted_value = self.extract_and_handle_output(extractor)

        assert_statement = AssertStatement(
            CompareExpression(
                # variable.get()
                FunctionCallExpression(
                    Attribute(self.response_data_variable, 'get'),
                    [Argument(extractor.field_name)],
                ),
                # ==
                compare_locator.get_comparison_for_value(extracted_value),
                # value
                Argument(extracted_value),
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

        # since we are trying to access the blocked tokens before even creating the statements, we need to prepare
        # the converter immediately
        self.prepare_converter()

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

        if not list_token and not length_token and not entry_token and not self.model_in_text_fits_request:
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

            # if there is a warning set number to 0 to get the first entry
            if not extractor.generates_warning:
                index = extracted_value - 1 if extracted_value > 0 else 0
            else:
                index = 0

            # use the index
            self.entry_variable = Variable('entry_{}'.format(index), self.model_adapter_from_request)
        else:
            self.entry_variable = None

    def get_token_to_extractor_list(self):
        token_extractor_list = super().get_token_to_extractor_list()
        if self.model_in_text_fits_request:
            token_extractor_list.append((self.model_in_text.token, IntegerExtractor))
        return token_extractor_list

    def get_entry_token(self):
        """Returns the token that represents the keyword entries in the doc."""
        return self.response_entry_locator.fittest_token or self.model_in_text.token

    def get_entry_extractor(self) -> Optional[Extractor]:
        """
        Return the extractor that is responsible for getting the index of the entry.
        """
        source = self.get_entry_token()

        if not source:
            return None

        wrapper = ConverterInitArgumentWrapper(token=source, representative=source)

        # always use an integer extractor -> which entry is meant?
        return self.get_extractor_instance(wrapper, IntegerExtractor)

    def get_document_compatibility(self):
        compatibility = super().get_document_compatibility()

        entry_extractor = self.get_entry_extractor()

        # if there is no extractor for the entry, we cannot determine which entry we should check
        if entry_extractor is None:
            compatibility *= 0.1
            return compatibility

        entry_token = self.get_entry_token()
        output_source = entry_extractor.output.output_token

        # if no entry number is defined, it is more unlikely that this converter does not fit
        if not output_source:
            compatibility *= 0.4

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
            extracted_number = extracted_number - 1 if extracted_number > 0 else 0

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

        if self.model_in_text_fits_request:
            return self.model_in_text.token

        return NoToken()

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
            compatibility *= 0.3

        # the length is normally described in numbers not in adjectives (`first` vs. `one`)
        output_source = length_extractor.output.output_token
        if output_source and output_source.pos_ == 'ADJ':
            compatibility *= 0.3

        return compatibility

    def prepare_statements(self, statements):
        statements = super().prepare_statements(statements)

        chunk = get_noun_chunk_of_token(self.get_length_token(), self.document)
        compare_locator = ComparisonLocator(chunk or self.document, reverse=False)

        length_extractor = self.get_length_extractor()
        extracted_value = self.extract_and_handle_output(length_extractor)

        if not length_extractor:
            return statements

        exp = CompareExpression(
            FunctionCallExpression('len', [Attribute(self.get_referenced_response_variable(), 'data')]),
            compare_locator.get_comparison_for_value(extracted_value),
            Argument(extracted_value),
        )
        statements.append(AssertStatement(exp))

        return statements
