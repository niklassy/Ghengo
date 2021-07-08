from nlp.extractor.exception import ExtractionError
from nlp.extractor.output import ExtractorOutput, VariableOutput, NumberAsStringOutput, StringOutput
from nlp.generate.warning import GenerationWarning
from nlp.utils import get_all_children, is_quoted, token_is_proper_noun, NoToken


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
        return '{} | {} -> {}'.format(self.__class__.__name__, str(self.source), self._extract_value())

    def get_output_kwargs(self):
        """
        Returns the kwargs that are passed to the ExtractorOutput __init__.
        """
        return {'source': self.source, 'document': self.document}

    def get_output_class(self):
        """Returns the output class of this extractor."""
        return self.output_class

    def get_output_instance(self) -> ExtractorOutput:
        """
        Returns an instance of ExtractorOutput.
        """
        output_class = self.get_output_class()
        return output_class(**self.get_output_kwargs())

    @classmethod
    def fits_input(cls, *args, **kwargs):
        """
        Can be used to check if this extractor fits for a given use case.
        """
        return False

    def _get_output_value(self, output_instance, token):
        """
        Is responsible for getting the value from the output instance. This method can also be overwritten if
        the extractor wants to change the value before returning it.
        """
        return output_instance.get_output(token)

    def _extract_value(self, output_instance=None, token=None):
        """
        A private method for extracting the value. It handles the case where the extractor searches for multiple
        values (defined by `self.many`).
        """
        if token is None:
            token = self.source

        if output_instance is None:
            output_instance = self.get_output_instance()

        try:
            return self._get_output_value(output_instance, token)
        except ExtractionError as e:
            return GenerationWarning.create_for_test_case(e.code, self.test_case)

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

    def get_child_extractor_kwargs(self):
        """Returns the kwargs that are passed to the child extractor __init__"""
        return {'document': self.document, 'source': self.source, 'test_case': self.test_case}

    def get_child_extractor_class(self):
        """Returns the child extractor class."""
        return self.child_extractor_class

    def skip_token_for_many(self, token):
        """
        Returns a boolean if the token should be skipped when handling a multi extraction.
        """
        output_class = self.get_output_class()

        # in case the child output class is for variables, skip tokens that are
        # unlikely to be one
        if issubclass(output_class, VariableOutput) or output_class == VariableOutput:
            return not token.is_digit and not token_is_proper_noun(token)

        # numbers can be digits
        if issubclass(output_class, NumberAsStringOutput):
            return not is_quoted(token) and not token.is_digit

        return not token.is_digit and not token_is_proper_noun(token) and not is_quoted(token)

    def _extract_value(self, output_instance=None, token=None):
        """
        Overwrite the normal _extract_value. If many is True, use `_extract_many` instead.
        """
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

        # if there is a list of values, these values are normally the children of the source
        for child in get_all_children(self.source):
            if not child or self.skip_token_for_many(child):
                continue

            # get the child extractor
            extractor_class = self.get_child_extractor_class()
            if extractor_class is None:
                continue

            # get the output class - which is the output from the child extractor
            output_instance = self.get_output_instance()

            # set the child as a source and tell the output that that token is the output
            output_instance.source_represents_output = True
            output_instance.source = child

            # get the output value from child extractor - don't call _extract_value from the child here
            # it is sufficient to use _get_output_value - it is also better to avoid recursive calls
            extractor = extractor_class(**self.get_child_extractor_kwargs())
            try:
                value = extractor._get_output_value(output_instance, child)
            except ExtractionError as e:
                value = GenerationWarning.create_for_test_case(e.code, self.test_case)

            output.append(value)

        return output


class StringExtractor(Extractor):
    output_class = StringOutput


class ManyExtractor(ManyExtractorMixin, Extractor):
    """A extractor base class that can be used for lists."""
    pass


class FieldExtractor(Extractor):
    """
    This is the base class for different fields.
    """
    default_field_class = None
    field_classes = ()

    def __init__(self, test_case, source, field, document):
        super().__init__(test_case=test_case, source=source, document=document)
        self.field = field

    @classmethod
    def fits_input(cls, field, *args, **kwargs):
        return isinstance(field, cls.field_classes)

    def _get_output_value(self, output_instance, token):
        output_value = super()._get_output_value(output_instance=output_instance, token=token)

        # if the field does not exist yet, see if there is any variable in the test case that matches the variable.
        # If yes, we assume that the variable is meant
        if isinstance(self.field, self.default_field_class):
            variable_output = VariableOutput(token, self.document, self.test_case.statements)

            try:
                return variable_output.get_output()
            except ExtractionError:
                pass

        return output_value
