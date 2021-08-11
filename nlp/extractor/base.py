from nlp.extractor.exception import ExtractionError
from nlp.extractor.output import ExtractorOutput, VariableOutput, NumberAsStringOutput, StringOutput, IntegerOutput
from nlp.generate.warning import GenerationWarning
from nlp.utils import get_all_children, is_quoted, get_next_token, token_can_represent_variable


class Extractor(object):
    """
    Extractors turn Tokens and strings into Python values that can be used in the generate part.
    """
    output_class = ExtractorOutput

    def __init__(self, test_case, representative, source, document, source_represents_output=False):
        self.test_case = test_case
        self.source = source
        self.document = document
        self.representative = representative
        self.source_represents_output = source_represents_output

    def __str__(self):
        return '{} | {} -> {}'.format(self.__class__.__name__, str(self.source), self._extract_value())

    @property
    def generates_warning(self):
        return len(self.get_generated_warnings()) > 0

    def get_generated_warnings(self):
        """
        Returns all the generation warnings that this extractor generated.
        """
        extracted_value = self.extract_value()
        return [extracted_value] if isinstance(extracted_value, GenerationWarning) else []

    def get_output_kwargs(self):
        """
        Returns the kwargs that are passed to the ExtractorOutput __init__.
        """
        return {'source': self.source, 'document': self.document}

    def get_output_class(self):
        """Returns the output class of this extractor."""
        return self.output_class

    @classmethod
    def fits_input(cls, *args, **kwargs):
        """
        Can be used to check if this extractor fits for a given use case.
        """
        return False

    @property
    def output(self) -> ExtractorOutput:
        """
        Returns the output instance that is used to extract the value and convert it to python.
        """
        output_class = self.get_output_class()
        instance = output_class(**self.get_output_kwargs())
        if self.source_represents_output:
            instance.source_represents_output = True

        return instance

    def _get_output_value(self, output_instance):
        """
        Is responsible for getting the value from the output instance. This method can also be overwritten if
        the extractor wants to change the value before returning it.
        """
        return output_instance.get_output()

    def _extract_value(self, output_instance=None):
        """
        A private method for extracting the value. It handles the case where the extractor searches for multiple
        values (defined by `self.many`).
        """
        if output_instance is None:
            output_instance = self.output

        try:
            return self._get_output_value(output_instance)
        except ExtractionError as e:
            return GenerationWarning(e.code)

    def extract_value(self):
        """
        The public method to extract the value. Every ExtractionError is caught here. If there is one, a
        GenerationWarning is returned instead.
        """
        return self._extract_value()

    def on_handled_by_converter(self, statements):
        """
        A method that is called by the converter after this extractor was handled. This can be useful in cases
        where the extractor has to add more statements to the existing ones or modify them in some ways.
        """
        pass


class ManyExtractorMixin(object):
    """
    This mixin can be used to enable a extractor to return multiple values of the selected output class.
    It could be easier to let lists be handled by an Output class. But there are some cases where the Extractor
    class above that wants to do something with the value returned by the Output class.

    This mixin will search for an extractor that would handle the input normally. It then repeatedly calls that
    extractor to get the output value from it.
    """
    child_extractor_class = Extractor

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.many = True

    def get_output_class(self):
        """
        By default the output class is the output class from the child extractor.
        """
        return self.get_child_extractor_class().output_class

    def get_generated_warnings(self):
        extracted_value = self._extract_many(token=self.source)
        if extracted_value is None:
            return []

        return [entry for entry in extracted_value if isinstance(entry, GenerationWarning)]

    def get_child_extractor_kwargs(self):
        """Returns the kwargs that are passed to the child extractor __init__"""
        return {
            'document': self.document,
            'source': self.source,
            'test_case': self.test_case,
            'representative': self.representative,
        }

    def get_child_extractor_class(self):
        """Returns the child extractor class."""
        return self.child_extractor_class

    def skip_token_for_many(self, token):
        """
        Returns a boolean if the token should be skipped when handling a multi extraction.
        """
        return not token_can_represent_variable(token)

    def _extract_value(self, output_instance=None, token=None):
        """
        Overwrite the normal _extract_value. If many is True, use `_extract_many` instead.
        """
        if token is None:
            token = self.source

        if self.many:
            return self._extract_many(output_instance, token)

        return super()._extract_value(output_instance, token)

    def _extract_many(self, output_instance=None, token=None):
        """
        This method is responsible for getting all values in the case that many is set to True.
        """
        output = []

        # check once more that many is set to true
        if not self.many:
            return self._extract_value(output_instance, token)

        children = get_all_children(token)

        # add the next token if it is quoted, just in case it was not recognized as a child
        next_token = get_next_token(token)
        if next_token and is_quoted(next_token) and next_token not in children:
            children = children + [next_token]

        # if there is a list of values, these values are normally the children of the source
        for child in children:
            if not child or self.skip_token_for_many(child):
                continue

            # get the child extractor
            extractor_class = self.get_child_extractor_class()
            if extractor_class is None:
                continue

            # get the output class - which is the output from the child extractor
            output_instance = self.output

            # set the child as a source and tell the output that that token is the output
            output_instance.source_represents_output = True
            output_instance.source = child

            # get the output value from child extractor - don't call _extract_value from the child here
            # it is sufficient to use _get_output_value - it is also better to avoid recursive calls
            extractor = extractor_class(**self.get_child_extractor_kwargs())
            try:
                value = extractor._get_output_value(output_instance)
            except ExtractionError as e:
                value = GenerationWarning(e.code)

            output.append(value)

        return output


class StringExtractor(Extractor):
    output_class = StringOutput


class IntegerExtractor(Extractor):
    output_class = IntegerOutput


class ManyExtractor(ManyExtractorMixin, Extractor):
    """A extractor base class that can be used for lists."""
    pass


class FieldExtractor(Extractor):
    """
    This is the base class for different fields.
    """
    default_field_class = None
    field_classes = ()

    def __init__(self, test_case, source, field_adapter, document, representative=None):
        # representative in kwargs to have the same signature as the init from the parent
        super().__init__(test_case=test_case, source=source, document=document, representative=field_adapter)
        self.field_adapter = field_adapter
        self.field = field_adapter.field

    @classmethod
    def fits_input(cls, field, *args, **kwargs):
        return isinstance(field, cls.field_classes)

    def _get_output_value(self, output_instance):
        output_value = super()._get_output_value(output_instance=output_instance)

        # if the field does not exist yet, see if there is any variable in the test case that matches the variable.
        # If yes, we assume that the variable is meant
        if isinstance(self.field, self.default_field_class):
            variable_output = VariableOutput(self.source, self.document, self.test_case)

            try:
                return variable_output.get_output()
            except ExtractionError:
                pass

        return output_value
