import ast
from decimal import Decimal

from spacy.tokens.token import Token

from nlp.extractor.exception import ExtractionError
from nlp.extractor.vocab import POSITIVE_BOOLEAN_INDICATORS, NEGATIVE_BOOLEAN_INDICATORS
from nlp.generate.expression import ModelFactoryExpression, CreateUploadFileExpression
from nlp.generate.variable import Variable
from nlp.generate.warning import NO_VALUE_FOUND_CODE, BOOLEAN_NO_SOURCE, VARIABLE_NOT_FOUND, GenerationWarning, \
    DICT_AS_STRING, FILE_NOT_FOUND
from nlp.utils import is_quoted, get_all_children, get_verb_for_token, token_is_negated, get_proper_noun_from_chunk, \
    get_noun_from_chunk, token_is_proper_noun, get_noun_chunk_of_token, get_noun_chunks


class ExtractorOutput(object):
    """
    This class represents the output from an extractor. It converts the source into a valid python value.
    The value can be accessed via `get_output`.
    """
    def __init__(self, source, document):
        self.source = source
        self.document = document
        self.source_represents_output = False

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False

        return self.get_output() == other.get_output() and self.source == other.source

    @classmethod
    def copy_from(cls, extractor_output):
        """Copies an output instance from another one. It moves all attributes over to the new instance."""
        copy = cls(document=extractor_output.document, source=extractor_output.source)
        copy.source_represents_output = extractor_output.source_represents_output
        return copy

    def guess_output_type(self, input_value):
        """
        This function will return a python value from a string. It will guess the type of
        that value from different criteria.
        """
        # if the value is already native, just return it
        if isinstance(input_value, (int, float, Decimal, bool)):
            return input_value

        # otherwise turn the value into a string to check it more
        value_str = str(input_value)

        # remove any quotations
        if is_quoted(value_str):
            value_str = value_str[1:-1]

            # any values in `<??>` are variables
            if value_str[0] == '<' and value_str[-1] == '>':
                return Variable(value_str, '')

        # try to return it as int or float
        try:
            return int(value_str)
        except ValueError:
            pass

        try:
            return float(value_str)
        except ValueError:
            pass

        # check for iterables
        try:
            literal_value = ast.literal_eval(value_str)
            if isinstance(literal_value, (list, tuple, set, dict)):
                return literal_value
        except (ValueError, SyntaxError):
            pass

        # check if the value may be a boolean
        bool_pos = POSITIVE_BOOLEAN_INDICATORS[self.document.lang_]
        bool_neg = NEGATIVE_BOOLEAN_INDICATORS[self.document.lang_]
        if value_str in bool_pos or value_str in bool_neg:
            return value_str in bool_pos

        # just return the value as a string
        return value_str

    def _get_value_from_previous_chunk(self, token):
        chunk = get_noun_chunk_of_token(token, token.doc)

        if chunk:
            noun_chunks = get_noun_chunks(self.document)

            try:
                chunk_index = noun_chunks.index(chunk)  # <- can raise ValueError if not in chunk
                previous_chunk = noun_chunks[chunk_index - 1]   # <- can raise IndexError if no previous chunk
                previous_propn = get_proper_noun_from_chunk(previous_chunk)

                if get_noun_from_chunk(previous_chunk) is None and previous_propn:
                    return str(previous_propn)
            except (IndexError, ValueError):
                pass

        raise ExtractionError(NO_VALUE_FOUND_CODE)

    def token_to_string_output(self, token):
        """
        This function handles the source token if it a Token. It uses the information that is passed from NLP
        to guess the token that holds the value. It will also turn that token into a value that is used in
        `guess_output_type` to guess the value.
        """
        # in some cases the parent might force that the source is the output
        if self.source_represents_output:
            return str(self.source)

        # if the token is an adjective or verb, it will most likely be a boolean field
        if token.pos_ == 'ADJ' or token.pos_ == 'VERB' or token.pos_ == 'ADV':

            # it is easier to determine from the verb if the adv is negated
            # `he is big` or `he is not big` - big is the ADV, is the AUX, not corresponds to the AUX
            if token.pos_ == 'ADV' and token.head.pos_ == 'AUX':
                token = token.head

            return not token_is_negated(token)

        # check if any children is a digit or a proper noun, if yes they are the value
        for child in token.children:
            if child.is_digit or token_is_proper_noun(child):
                return str(child)

        try:
            # as an alternative, if the next token is in quotes it should be the value
            next_token = self.document[token.i + 1]
            if is_quoted(next_token):
                return str(next_token)
        except IndexError:
            pass

        # if still nothing is found, the value might be in a previous noun chunk
        try:
            return self._get_value_from_previous_chunk(token)
        except ExtractionError:
            pass

        raise ExtractionError(NO_VALUE_FOUND_CODE)

    def get_output(self, token=None):
        """
        The function that returns the output. You can pass a specific token to check
        the output. If you pass nothing, the source of this class is used.
        """
        if token is None:
            token = self.source

        # if the input is not a token, we can only guess its type
        if not isinstance(token, Token):
            return self.guess_output_type(token)

        return self.guess_output_type(self.token_to_string_output(token))


class NoneOutput(ExtractorOutput):
    """
    This output will always return None.
    """
    def get_output(self, token=None):
        return None


class StringOutput(ExtractorOutput):
    def get_output(self, token=None):
        return str(super().get_output(token))


class DictOutput(ExtractorOutput):
    def get_output(self, token=None):
        output = super().get_output(token)

        if not isinstance(output, dict):
            raise ExtractionError(DICT_AS_STRING)

        return output


class NumberAsStringOutput(ExtractorOutput):
    """
    This output is a base class for several numbers. Numbers can be found in different places than other data.
    """
    def guess_output_type(self, input_value):
        if isinstance(input_value, (int, float, Decimal)):
            return input_value

        value_str = str(input_value)

        # remove any quotations
        if is_quoted(value_str):
            value_str = value_str[1:-1]

        try:
            float(value_str)
            return value_str
        except ValueError:
            raise ExtractionError(NO_VALUE_FOUND_CODE)

    def token_to_string_output(self, token):
        if self.source_represents_output:
            return str(self.source)

        for child in get_all_children(token):
            if child.is_digit:
                return str(child)

        try:
            # as an alternative, if the next token is in quotes it should be the value
            next_token = self.document[token.i + 1]
            if is_quoted(next_token):
                clean_next_token_str = str(next_token)[1:-1]

                try:
                    float(clean_next_token_str)
                    return clean_next_token_str
                except ValueError:
                    pass

        except IndexError:
            pass

        if token.is_digit:
            return str(token)

        raise ExtractionError(NO_VALUE_FOUND_CODE)


class IntegerOutput(NumberAsStringOutput):
    """
    This output will return an integer.
    """
    def get_output(self, token=None):
        return int(super().get_output(token))


class FloatOutput(NumberAsStringOutput):
    """
    This output will return a float.
    """
    def get_output(self, token=None):
        return float(super().get_output(token))


class DecimalOutput(NumberAsStringOutput):
    """
    This output will return a decimal.
    """
    def get_output(self, token=None):
        return Decimal(super().get_output(token))


class BooleanOutput(ExtractorOutput):
    """
    This output will return a boolean.
    """
    def guess_output_type(self, input_value):
        """If only handling a string, check if the value indicates a positive value."""
        if isinstance(input_value, bool):
            return input_value

        if is_quoted(input_value):
            input_value = input_value[1:-1]

        return input_value in POSITIVE_BOOLEAN_INDICATORS[self.document.lang_]

    def token_to_string_output(self, token):
        """While handling a token, get the verb of the token and determine if the verb and/or the token are negated."""
        if self.source_represents_output:
            return str(self.source)

        verb = get_verb_for_token(token)
        token_value_true = not token_is_negated(token)

        if not verb:
            return token_value_true

        verb_value_true = not token_is_negated(verb)
        return verb_value_true and token_value_true


class VariableOutput(ExtractorOutput):
    """
    This will always return a variable. Since variables always reference an earlier statement, this output
    needs the statements. It will search for a statement with a similar variable and returns it if possible.
    """
    def __init__(self, source, document, test_case):
        super().__init__(source, document)
        self.test_case = test_case
        self.statements = test_case.statements

    @classmethod
    def copy_from(cls, extractor_output):
        copy = super().copy_from(extractor_output)

        if hasattr(extractor_output, 'statements'):
            copy.statements = extractor_output.statements
        else:
            copy.statements = []

        return copy

    def statement_matches_output(self, statement, output):
        """Can be used to define if a the variable of a statement is okay and can be returned."""
        return statement.string_matches_variable(output, reference_string=None)

    def skip_statement(self, statement):
        """Can be used to define if a statement should be skipped."""
        return False

    def guess_output_type(self, input_value):
        output = super().guess_output_type(input_value)

        for statement in self.statements:
            if self.skip_statement(statement):
                continue

            if self.statement_matches_output(statement, str(output)):
                return statement.variable.copy()

        raise ExtractionError(VARIABLE_NOT_FOUND)


class FileVariableOutput(VariableOutput):
    """
    A variable output that is related to files.
    """
    def token_to_string_output(self, token):
        try:
            return super().token_to_string_output(token)
        except ExtractionError:
            raise ExtractionError(FILE_NOT_FOUND)

    def guess_output_type(self, input_value):
        try:
            return super().guess_output_type(input_value)
        except ExtractionError:
            raise ExtractionError(FILE_NOT_FOUND)

    def skip_statement(self, statement):
        return not isinstance(statement.expression, CreateUploadFileExpression)


class ModelVariableOutput(VariableOutput):
    """
    This output works exactly the same as `VariableOutput`. The difference is that is only returns variables
    of a given model. That model must be given to this class on init.
    """
    def __init__(self, source, document, test_case, model):
        super().__init__(source, document, test_case)
        self.model = model

    @classmethod
    def copy_from(cls, extractor_output):
        copy = super().copy_from(extractor_output)

        if hasattr(extractor_output, 'model'):
            copy.model = extractor_output.model
        else:
            copy.model = None

        return copy

    def skip_statement(self, statement):
        """Skip statements that don't create a model."""
        return not isinstance(statement.expression, ModelFactoryExpression)

    def statement_matches_output(self, statement, output):
        """A statement is valid if the model is the same and the reference string matches."""
        expression_model = statement.expression.model_adapter.model
        statement_variable_matches = statement.string_matches_variable(output, reference_string=self.model.__name__)

        return expression_model == self.model and statement_variable_matches
