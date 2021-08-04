from django.core.files.uploadedfile import SimpleUploadedFile

from nlp.converter.base.converter import ClassConverter
from nlp.converter.property import FileProperty, NewFileVariableProperty
from nlp.converter.wrapper import ConverterInitArgumentWrapper
from nlp.extractor.base import StringExtractor
from nlp.generate.argument import Kwarg
from nlp.generate.expression import CreateUploadFileExpression
from nlp.generate.statement import AssignmentStatement
from nlp.locator import FileExtensionLocator
from nlp.searcher import ClassArgumentSearcher


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
