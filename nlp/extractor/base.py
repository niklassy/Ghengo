from nlp.extractor.exception import ExtractionError
from nlp.extractor.output import ExtractorOutput, VariableOutput
from nlp.generate.warning import GenerationWarning


class Extractor(object):
    """
    Extractors turn Tokens and strings into Python values that can be used in the generate part.
    """
    output_class = ExtractorOutput

    def __init__(self, test_case, source, document):
        self.test_case = test_case
        self.source = source
        self.document = document

    def __str__(self):
        return '{} | {} -> {}'.format(self.__class__.__name__, str(self.source), self.extract_value())

    def get_output_kwargs(self):
        return {'source': self.source, 'document': self.document}

    def get_output_instance(self) -> ExtractorOutput:
        return self.output_class(**self.get_output_kwargs())

    @classmethod
    def fits_input(cls, *args, **kwargs):
        return False

    def _extract_value(self):
        return self.get_output_instance().get_output(self.source)

    def extract_value(self):
        try:
            return self._extract_value()
        except ExtractionError as e:
            return GenerationWarning.create_for_test_case(e.code, self.test_case)

    def on_handled_by_converter(self, statements):
        pass


class FieldExtractor(Extractor):
    default_field_class = None
    field_classes = ()

    def __init__(self, test_case, source, field, document):
        super().__init__(test_case=test_case, source=source, document=document)
        self.field = field

    @classmethod
    def fits_input(cls, field, *args, **kwargs):
        return isinstance(field, cls.field_classes)

    def _extract_value(self):
        extracted_value = super()._extract_value()

        # if the field does not exist yet, see if there is any variable in the test case that matches the variable.
        # If yes, we assume that the variable is meant
        if isinstance(self.field, self.default_field_class):
            variable_output = VariableOutput(self.source, self.document, self.test_case.statements)

            try:
                return variable_output.get_output()
            except ExtractionError:
                pass

        return extracted_value
