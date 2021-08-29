from typing import Optional

from django_meta.model import AbstractModelFieldWrapper
from nlp.converter.base.converter import ClassConverter
from nlp.converter.property import NewModelProperty, ReferenceModelVariableProperty
from nlp.converter.wrapper import ConverterInitArgumentWrapper
from nlp.extractor.base import IntegerExtractor, Extractor, StringExtractor
from nlp.extractor.fields_model import ModelFieldExtractor, get_model_field_extractor
from nlp.extractor.fields_rest_api import ApiModelFieldExtractor, get_api_model_field_extractor
from nlp.generate.argument import Argument
from nlp.generate.attribute import Attribute
from nlp.generate.constants import CompareChar
from nlp.generate.expression import CompareExpression, FunctionCallExpression, Expression, RequestExpression, \
    ModelFactoryExpression
from nlp.generate.index import Index
from nlp.generate.statement import AssertStatement, AssignmentStatement
from nlp.generate.variable import Variable, VariableReference
from nlp.lookout.project import SerializerFieldLookout, ModelFieldLookout
from nlp.lookout.token import NounLookout, ComparisonLookout, VerbLookout
from nlp.utils import get_noun_chunk_of_token, NoToken, token_is_definite, get_previous_token


class ResponseConverterBase(ClassConverter):
    """
    This is the base class for all converters that relate to the response.
    """
    field_lookout_classes = [SerializerFieldLookout, ModelFieldLookout]

    def __init__(self, document, related_object, django_project, test_case):
        super().__init__(document, related_object, django_project, test_case)

        # create some lookouts that look for certain keywords:
        self.status_lookout = NounLookout(self.document, 'status')  # <- status of response
        self.status_lookout.locate()

        self.response_lookout = NounLookout(self.document, 'response')  # <- response itself
        self.response_lookout.locate()

        self.error_lookout = NounLookout(self.document, 'error')  # <- error
        self.error_lookout.locate()

        self.model_in_text = NewModelProperty(self, blocked_tokens=self._blocked_argument_tokens)
        self.model_in_text_var = ReferenceModelVariableProperty(self, self.model_in_text)

    @property
    def model_wrapper_from_request(self):
        """Returns the model_wrapper that is referenced by the variable of the request."""
        referenced_variable = self.get_referenced_response_variable()

        if not referenced_variable:
            return None

        return referenced_variable.value.url_wrapper.model_wrapper

    @property
    def model_in_text_fits_request(self):
        """Checks if the model in the text is valid and fits to the one provided by the request."""
        model_wrapper = self.model_wrapper_from_request

        if not model_wrapper:
            return False

        return model_wrapper.models_are_equal(self.model_in_text.value)

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
            (self.status_lookout.fittest_token, IntegerExtractor),
            (self.error_lookout.fittest_token, StringExtractor),
        ]

    def get_extractor_class(self, argument_wrapper: ConverterInitArgumentWrapper):
        """Can use serializer, model fields and the custom extractors."""
        lookout_extractor_map = self._token_to_extractor_map

        if argument_wrapper.token and argument_wrapper.token in lookout_extractor_map:
            return lookout_extractor_map[argument_wrapper.token]

        if isinstance(argument_wrapper.representative, AbstractModelFieldWrapper):
            return get_model_field_extractor(argument_wrapper.representative.field)

        return get_api_model_field_extractor(argument_wrapper.representative.field)

    def get_extractor_kwargs(self, argument_wrapper, extractor_cls):
        """Add the model and the field to the kwargs."""
        kwargs = super().get_extractor_kwargs(argument_wrapper, extractor_cls)

        if extractor_cls == ApiModelFieldExtractor or issubclass(extractor_cls, ApiModelFieldExtractor):
            kwargs['field_wrapper'] = argument_wrapper.representative

        # since the class may be for model fields or REST fields, add the model_wrapper if needed
        if issubclass(extractor_cls, ModelFieldExtractor) or extractor_cls == ModelFieldExtractor:
            kwargs['model_wrapper'] = self.model_wrapper_from_request
            kwargs['field_wrapper'] = argument_wrapper.representative

        return kwargs

    def get_lookout_kwargs(self):
        serializer_class = self.get_referenced_response_variable().value.serializer_class

        return {
            'serializer': serializer_class() if serializer_class else None,
            'model_wrapper': self.model_wrapper_from_request,
        }

    def prepare_converter(self):
        self.block_token_as_argument(self.status_lookout.fittest_token)
        self.block_token_as_argument(self.response_lookout.fittest_token)

        # only block the model in text if it is actually equal to the one the serializer returns
        if self.model_in_text_fits_request:
            self.block_token_as_argument(self.model_in_text.token)

    def get_document_compatibility(self):
        compatibility = 1

        # if there was no request previously, it is unlikely that this converter is compatible
        if not any([isinstance(s.expression, RequestExpression) for s in self.test_case.statements]):
            compatibility *= 0.1

        # if there is a model variable in the text, it is more likely that it is meant instead
        if self.model_in_text_var.value:
            compatibility *= 0.7

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
        if not self.response_lookout.fittest_token:
            return valid_variables[-1].get_reference()

        wrapper = ConverterInitArgumentWrapper(
            representative=self.response_lookout.fittest_keyword,
            token=self.response_lookout.fittest_token,
        )

        # always get the integer for the response -> which response is meant?
        response_extractor = self.get_extractor_instance(wrapper, IntegerExtractor)
        if response_extractor.generates_warning:
            return valid_variables[-1].get_reference()

        # if the return value is fine, extract the number and try to access it from all the variables
        response_number = response_extractor.extract_value()
        try:
            return valid_variables[response_number - 1].get_reference()
        except IndexError:
            return valid_variables[-1].get_reference()

    def extract_and_handle_output(self, extractor):
        extracted_value = super().extract_and_handle_output(extractor)

        # since we are currently not supporting nested objects, if a model variable is returned from the extractor
        # use the pk instead of that variable
        value_holds_variable = isinstance(extracted_value, (Variable, VariableReference))
        if value_holds_variable and isinstance(extracted_value.value, ModelFactoryExpression):
            return Attribute(extracted_value, 'pk')

        return extracted_value


class ResponseStatusCodeConverter(ResponseConverterBase):
    """
    This converter is responsible for checking the status code of a response.
    """
    field_lookout_classes = []

    def get_document_compatibility(self):
        compatibility = super().get_document_compatibility()

        if not self.status_lookout.fittest_token:
            compatibility *= 0.2

        return compatibility

    def prepare_statements(self, statements):
        if self.status_lookout.fittest_token:
            response_var = self.get_referenced_response_variable()

            wrapper = ConverterInitArgumentWrapper(
                token=self.status_lookout.fittest_token,
                representative=self.status_lookout.fittest_keyword
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
    field_lookout_classes = []

    def get_document_compatibility(self):
        compatibility = super().get_document_compatibility()

        if not self.error_lookout.fittest_token:
            compatibility *= 0.2

        return compatibility

    def prepare_statements(self, statements):
        if self.error_lookout.fittest_token:
            response_var = self.get_referenced_response_variable()

            wrapper = ConverterInitArgumentWrapper(
                token=self.error_lookout.fittest_token,
                representative=self.error_lookout.fittest_keyword
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
        if not self.response_lookout.fittest_token:

            # check if there is a model in the text, if not it is very unlikely to fit
            if self.model_in_text.token:
                token_before = get_previous_token(self.model_in_text.token)

                # if there is a model token and it fits the request model, this is likely to fit though if
                # the word before is definite (`der Auftrag`, `the order`)
                # YES => Dann sollte *der* Auftrag den Namen "sa" haben
                # NO  => Dann sollte *ein* Auftrag mit dem Namen "asd" existieren
                if self.model_in_text_fits_request and token_is_definite(token_before):
                    compatibility *= 1
                else:
                    compatibility *= 0.5
            else:
                compatibility *= 0.2

        return compatibility

    @property
    def response_data_variable_already_present(self):
        """Check if the response variable is already present in the test case."""
        response_variable = self.response_data_variable
        return self.test_case.variable_defined(response_variable.name_predetermined, response_variable.reference_string)

    @property
    def response_data_variable(self):
        if self._response_data_variable is None:
            self._response_data_variable = Variable(
                'resp_data',
                self.model_wrapper_from_request.name if self.model_wrapper_from_request else '',
            )
        return self._response_data_variable

    def prepare_statements(self, statements):
        """
        First, save the data field in a separate variable to have easier access later on.
        """
        statements = super().prepare_statements(statements)

        if len(self.extractors) > 0 and not self.response_data_variable_already_present:
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
        compare_lookout = ComparisonLookout(chunk or self.document, reverse=False)
        extracted_value = self.extract_and_handle_output(extractor)

        assert_statement = AssertStatement(
            CompareExpression(
                # variable.get()
                FunctionCallExpression(
                    Attribute(self.response_data_variable.get_reference(), 'get'),
                    [Argument(extractor.field_name)],
                ),
                # ==
                compare_lookout.get_comparison_for_value(extracted_value),
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
        self.response_list_lookout = NounLookout(self.document, 'list')
        self.response_list_lookout.locate()

        self.response_length_lookout = NounLookout(self.document, 'length')
        self.response_length_lookout.locate()

        self.response_entry_lookout = NounLookout(self.document, 'entry')
        self.response_entry_lookout.locate()

        # since we are trying to access the blocked tokens before even creating the statements, we need to prepare
        # the converter immediately
        self.prepare_converter()

    def prepare_converter(self):
        self.block_token_as_argument(self.response_list_lookout.fittest_token)
        self.block_token_as_argument(self.response_length_lookout.fittest_token)
        self.block_token_as_argument(self.response_entry_lookout.fittest_token)
        # keep this at the end
        super().prepare_converter()

    def get_token_to_extractor_list(self):
        token_lookout_list = super().get_token_to_extractor_list()

        token_lookout_list.append((self.response_length_lookout.fittest_token, IntegerExtractor))
        token_lookout_list.append((self.response_entry_lookout.fittest_token, IntegerExtractor))

        return token_lookout_list

    def get_document_compatibility(self):
        compatibility = super().get_document_compatibility()

        # if a list is mentioned, the response will most likely be a list
        list_token = self.response_list_lookout.fittest_token

        # if the length of the response is checked, most likely multiple objects are returned
        length_token = self.response_length_lookout.fittest_token

        # if there is the word `entry` it is likely that multiple objects are returned
        entry_token = self.response_entry_lookout.fittest_token

        if not list_token and not length_token and not entry_token:
            if not self.model_in_text_fits_request:
                compatibility *= 0.3
            else:
                # if there is a model token that fits, check for a verb like contain or return that reference the
                # request
                verb_lookout = VerbLookout(self.document, words=['to contain', 'to return'])
                verb_lookout.locate()

                if not verb_lookout.fittest_token:
                    compatibility *= 0.8

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
            self.entry_variable = Variable('entry_{}'.format(index), self.model_wrapper_from_request.name)
        else:
            self.entry_variable = None

    def get_token_to_extractor_list(self):
        token_extractor_list = super().get_token_to_extractor_list()
        if self.model_in_text_fits_request:
            token_extractor_list.append((self.model_in_text.token, IntegerExtractor))
        return token_extractor_list

    def get_entry_token(self):
        """Returns the token that represents the keyword entries in the doc."""
        return self.response_entry_lookout.fittest_token or self.model_in_text.token

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
        if entry_extractor is None or compatibility < 0.7:
            compatibility *= 0.1
            return compatibility

        # this converter is more likely determined by the entry token, so we need to negate it and start from scratch
        compatibility = 1
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
                    Attribute(self.entry_variable.get_reference(), 'get'),
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
    field_lookout_classes = []

    def get_token_to_extractor_list(self):
        token_extractor_list = super().get_token_to_extractor_list()
        token_extractor_list.append((self.get_length_token(), IntegerExtractor))
        return token_extractor_list

    def get_length_token(self):
        """
        Returns the token that represents the length of the response.
        """
        fittest_token = self.response_length_lookout.fittest_token or self.response_entry_lookout.fittest_token

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
        compare_lookout = ComparisonLookout(chunk or self.document, reverse=False)

        length_extractor = self.get_length_extractor()
        extracted_value = self.extract_and_handle_output(length_extractor)

        if not length_extractor:
            return statements

        exp = CompareExpression(
            FunctionCallExpression('len', [Attribute(self.get_referenced_response_variable(), 'data')]),
            compare_lookout.get_comparison_for_value(extracted_value),
            Argument(extracted_value),
        )
        statements.append(AssertStatement(exp))

        return statements
