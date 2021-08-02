import ast
from decimal import Decimal
from typing import Union, Tuple, Any

from spacy.tokens.token import Token

from core.exception import LanguageNotSupported
from nlp.extractor.exception import ExtractionError
from nlp.extractor.vocab import POSITIVE_BOOLEAN_INDICATORS, NEGATIVE_BOOLEAN_INDICATORS
from nlp.generate.expression import ModelFactoryExpression, CreateUploadFileExpression
from nlp.generate.variable import Variable
from nlp.generate.warning import NO_VALUE_FOUND_CODE, VARIABLE_NOT_FOUND, DICT_AS_STRING, FILE_NOT_FOUND, NUMBER_ERROR
from nlp.utils import is_quoted, get_all_children, get_verb_for_token, token_is_negated, \
    token_is_proper_noun, token_is_like_num, \
    num_word_to_integer, get_next_token, NoToken, get_propn_from_previous_chunk


class ExtractorOutput(object):
    """
    This class represents the output from an extractor. It converts the source into a valid python value.
    The value can be accessed via `get_output`.
    """
    supports_variable_source = True

    class NoOutputYet:
        def __bool__(self):
            return False

    def __init__(self, source, document):
        self.source = source
        self.document = document
        self.source_represents_output = False

        self._output_token = self.NoOutputYet()

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False

        return self.get_output() == other.get_output() and self.source == other.source

    @property
    def source_is_token(self):
        """Returns if the source of this output is a Token."""
        return isinstance(self.source, Token)

    @property
    def source_is_python_value(self):
        """Returns if the source of this output is a Token."""
        return not self.source_is_token

    @classmethod
    def string_represents_variable(cls, string):
        """
        Checks if a given string represents a variable. Normally this is the case for
        "<foo>" and <foo>.
        """
        clean_string = str(string)
        if is_quoted(string):
            clean_string = clean_string[1:-1]

        return len(clean_string) > 2 and clean_string[0] == '<' and clean_string[-1] == '>'

    @property
    def output_token(self) -> Union[NoToken, Token]:
        """
        Returns the source that was used to actually get the output.

        If there was an exception or no output token is found, NoToken is returned. Else the token that
        was used to get the output is returned. The output token is actually fully determined in `_get_output`.
        """
        if isinstance(self._output_token, self.NoOutputYet):
            try:
                self.get_output()
            except ExtractionError:
                self._output_token = NoToken()

        return self._output_token

    @classmethod
    def copy_from(cls, extractor_output):
        """Copies an output instance from another one. It moves all attributes over to the new instance."""
        copy = cls(document=extractor_output.document, source=extractor_output.source)
        copy.source_represents_output = extractor_output.source_represents_output
        return copy

    def handle_variable_value(self, value):
        """This method is responsible for handling variables."""
        value_str = str(value)

        if is_quoted(value_str):
            value_str = value_str[1:-1]

        # any values in `<??>` are variables
        if self.string_represents_variable(value_str):
            return Variable(value_str[1:-1], '')

        raise ValueError()

    def get_output_from_python_value(self, python_value):
        """
        This method will actually return the value that will be the output. This value will be prepared one last
        time before it is returned. This method is also used if the source is not a Token.
        """
        # numbers, decimals and boolean values are simple returned
        if isinstance(python_value, (int, float, Decimal, bool)):
            return python_value

        # otherwise turn the value into a string to check it more
        value_str = str(python_value)
        if is_quoted(value_str):
            value_str = value_str[1:-1]

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

    def token_to_python(self, token) -> Tuple[Any, Token]:
        """
        Transforms a given token to a first string that will/ may be analyzed further later.
        This base version will try to make assumptions about the python type by checking information about the
        token.

        This will return a tuple containing the python value and the token that was used to get that python value.
        """
        if token.pos_ == 'ADJ' or token.pos_ == 'VERB' or token.pos_ == 'ADV':
            # it is easier to determine from the verb if the adv is negated
            # `he is big` or `he is not big` - big is the ADV, is the AUX, not corresponds to the AUX
            if token.pos_ == 'ADV' and token.head.pos_ == 'AUX':
                token = token.head

            children_negated = any([token_is_negated(child) for child in get_all_children(token)])
            boolean_value = not token_is_negated(token) and not children_negated
            return boolean_value, token

        # check if any children is a digit or a proper noun, if yes they are the value
        for child in token.children:
            if child.is_digit or token_is_proper_noun(child):
                return str(child), child

        # as an alternative, if the next token is in quotes it should be the value
        next_token = get_next_token(token)
        if is_quoted(next_token):
            return str(next_token)[1:-1], next_token

        # if still nothing is found, the value might be in a previous noun chunk
        previous_token = get_propn_from_previous_chunk(token)
        if previous_token:
            return str(previous_token), previous_token

        raise ExtractionError(NO_VALUE_FOUND_CODE)

    def set_output_token(self, token):
        """
        Sets the output token - the one that was actually used to get the python value.
        """
        self._output_token = token

    def prepare_output(self, output_value):
        """
        Is called right before the output is returned. Can used to change the return value.
        """
        return output_value

    def prepare_python_value(self, value):
        """
        Is called right before `get_output_from_python_value` is called. It can be used to modify the value.
        This is useful if the value needs to modified every time.
        """
        return str(value)

    def _get_output(self):
        """
        This is the private function that gets the output.
        """
        token = self.source

        python_value = token
        output_token = NoToken()

        try:
            # if the source is a token (is true most of the time)
            if self.source_is_token:
                # check if the token represents the output - if yes, set it as output token and convert to python
                if self.source_represents_output:
                    output_token = self.source
                    python_value = str(self.source)
                else:
                    # if not use `token_to_python` to get the python value and the output token
                    python_value, output_token = self.token_to_python(token)

            # set the output token afterwards - if the source holds no token, it will be NoToken
            self.set_output_token(output_token)

            # if the output represents a variable ('<value'), return that instead
            if self.supports_variable_source and self.string_represents_variable(python_value):
                return self.handle_variable_value(python_value)

            # prepare the value before getting the output, this can be useful if a class always needs to change
            # value before the final output
            prepared_value = self.prepare_python_value(python_value)
            output = self.get_output_from_python_value(prepared_value)

            # return the output
            return self.prepare_output(output)
        except ExtractionError as e:
            # if there is any error during the whole process, set the output token to NoToken and raise the error
            # again
            self.set_output_token(NoToken())
            raise e

    def get_output(self):
        """
        The function that returns the output. You can pass a specific token to check
        the output. If you pass nothing, the source of this class is used.
        """
        return self._get_output()


class NoneOutput(ExtractorOutput):
    """
    This output will always return None.
    """
    def _get_output(self):
        self.set_output_token(NoToken())
        return None


class StringOutput(ExtractorOutput):
    def prepare_output(self, output_value):
        return str(output_value)


class DictOutput(ExtractorOutput):
    def prepare_output(self, output_value):
        if not isinstance(output_value, dict):
            raise ExtractionError(DICT_AS_STRING)

        return output_value


class NumberAsStringOutput(ExtractorOutput):
    """
    This output is a base class for several numbers. Numbers can be found in different places than other data.
    """
    def prepare_python_value(self, value):
        token = self.output_token

        if token and self.token_can_be_parsed_to_int(token):
            try:
                return str(self.token_to_integer(token, raise_exception=True))
            except ValueError:
                raise ExtractionError(NUMBER_ERROR)

        return super().prepare_python_value(value)

    def token_to_python(self, token):
        for child in get_all_children(token):
            if child.is_digit or self.token_can_be_parsed_to_int(child):
                return str(child), child

        # as an alternative, if the next token is in quotes it should be the value
        next_token = get_next_token(token)
        if is_quoted(next_token):
            clean_next_token_str = str(next_token)[1:-1]

            if self.token_can_be_parsed_to_int(next_token) or self.string_represents_variable(clean_next_token_str):
                return str(next_token), next_token

            try:
                float(clean_next_token_str)
                return clean_next_token_str, next_token
            except ValueError:
                pass

        if token.is_digit:
            return str(token), token

        raise ExtractionError(NO_VALUE_FOUND_CODE)

    def get_output_from_python_value(self, python_value):
        """
        Only accept values that can become numbers.
        """
        if isinstance(python_value, (int, float, Decimal)):
            return python_value

        value_str = str(python_value)

        try:
            float(value_str)
            return value_str
        except ValueError:
            raise ExtractionError(NO_VALUE_FOUND_CODE)

    def token_to_integer(self, token, raise_exception=False):
        """
        Translates a token to an integer, if it works either an exception is raised or None
        returned.
        """
        try:
            return num_word_to_integer(str(token), self.document.lang_)
        except (ValueError, LanguageNotSupported):
            try:
                return num_word_to_integer(str(token.lemma_), self.document.lang_)
            except (ValueError, LanguageNotSupported):
                if raise_exception:
                    raise ValueError()

        return None

    def token_can_be_parsed_to_int(self, token):
        """
        Checks if a given token can be parsed to an int
        """
        try:
            self.token_to_integer(token, raise_exception=True)
        except ValueError:
            return False

        return token_is_like_num(token)


class IntegerOutput(NumberAsStringOutput):
    """
    This output will return an integer.
    """
    def prepare_output(self, output_value):
        output_value = super().prepare_output(output_value)

        # if there is a string that represents a float, try to convert it to a float and to int afterwards
        try:
            output_value = float(output_value)
        except ValueError:
            pass

        return int(output_value)


class FloatOutput(NumberAsStringOutput):
    """
    This output will return a float.
    """
    def prepare_output(self, output_value):
        return float(super().prepare_output(output_value))


class DecimalOutput(NumberAsStringOutput):
    """
    This output will return a decimal.
    """
    def prepare_output(self, output_value):
        return Decimal(super().prepare_output(output_value))


class BooleanOutput(ExtractorOutput):
    """
    This output will return a boolean.
    """
    def token_to_python(self, token):
        # while is does not really make sense to represent values as variables when using a boolean (is normally
        # determined via the verb and its negation), still we catch the case here
        if self.string_represents_variable(token):
            return str(token), token

        verb = get_verb_for_token(token)
        token_value_true = not token_is_negated(token)

        if not verb:
            return token_value_true, token

        verb_value_true = not token_is_negated(verb)
        boolean_value = verb_value_true and token_value_true
        return boolean_value, verb

    def get_output_from_python_value(self, python_value):
        if isinstance(python_value, bool):
            return python_value

        return python_value in POSITIVE_BOOLEAN_INDICATORS[self.document.lang_]


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

    def get_output_from_python_value(self, python_value):
        python_value = super().get_output_from_python_value(python_value)

        for statement in self.statements:
            if self.skip_statement(statement):
                continue

            if self.statement_matches_output(statement, str(python_value)):
                return statement.variable.copy()

        raise ExtractionError(VARIABLE_NOT_FOUND)


class FileVariableOutput(VariableOutput):
    """
    A variable output that is related to files.
    """
    def _get_output(self):
        try:
            return super()._get_output()
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
