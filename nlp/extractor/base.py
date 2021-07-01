from nlp.extractor.exception import ExtractionError
from nlp.extractor.vocab import NEGATIVE_BOOLEAN_INDICATORS, POSITIVE_BOOLEAN_INDICATORS
from nlp.generate.variable import Variable
from nlp.generate.warning import GenerationWarning
from nlp.utils import is_quoted


class Extractor(object):
    """
    Extractors turn Tokens and strings into Python values that can be used in the generate part.
    """
    def __init__(self, test_case, source, document):
        self.test_case = test_case
        self.source = source
        self.document = document

    def __str__(self):
        return '{} | {} -> {}'.format(self.__class__.__name__, str(self.source), self.extract_value())

    @classmethod
    def fits_input(cls, *args, **kwargs):
        return False

    def get_guessed_python_value(self, string):
        """
        Uses a string as an input to get a python value that may fit that string.
        """
        value_str = str(string)

        # remove any quotations
        if is_quoted(value_str):
            value_str = value_str[1:-1]

            if value_str[0] == '<' and value_str[-1] == '>':
                return Variable(value_str, '')

        # try to get int
        try:
            return int(value_str)
        except ValueError:
            pass

        # try float value
        try:
            return float(value_str)
        except ValueError:
            pass

        # check if the value may be a boolean
        bool_pos = POSITIVE_BOOLEAN_INDICATORS[self.document.lang_]
        bool_neg = NEGATIVE_BOOLEAN_INDICATORS[self.document.lang_]
        if value_str in bool_pos or value_str in bool_neg:
            return value_str in bool_pos

        # just return the value
        return value_str

    def _extract_value(self):
        return self.get_guessed_python_value(self.source)

    def extract_value(self):
        try:
            return self._extract_value()
        except ExtractionError as e:
            return GenerationWarning.create_for_test_case(e.code, self.test_case)

    def on_handled_by_converter(self, statements):
        pass
