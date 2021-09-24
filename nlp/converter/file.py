from django.core.files.uploadedfile import SimpleUploadedFile

from nlp.converter.base.converter import ClassConverter
from nlp.converter.property import FileProperty, NewFileVariableProperty
from nlp.converter.wrapper import ReferenceTokenWrapper
from nlp.extractor.base import StringExtractor
from nlp.generate.argument import Kwarg
from nlp.generate.expression import CreateUploadFileExpression
from nlp.generate.statement import AssignmentStatement
from nlp.lookout.project import ClassArgumentLookout
from nlp.lookout.token import FileExtensionLookout


class FileConverter(ClassConverter):
    """
    This converter can create statements that are used to create files.
    """
    can_use_datatables = True
    field_lookout_classes = [ClassArgumentLookout]

    class ArgumentReferences:
        """The names for the arguments from SimpleUploadedFile"""
        CONTENT = 'content'
        NAME = 'name'

        @classmethod
        def get_all(cls):
            return [cls.CONTENT, cls.NAME]

    def __init__(self, document, related_object, django_project, test_case):
        super().__init__(document, related_object, django_project, test_case)
        # get the extension of the file
        self.file_extension_lookout = FileExtensionLookout(self.document)

        self.file = FileProperty(self)
        self.file_variable = NewFileVariableProperty(self)

    def prepare_converter(self):
        self.file_extension_lookout.locate()
        # Reject tokens that represent the file, the variable or the extension.
        for t in (self.file.token, self.file_variable.token, self.file_extension_lookout.fittest_token):
            self.block_token_as_reference(t)

    def get_document_compatibility(self):
        """Only if a file token was found this converter makes sense."""
        if self.file.token:
            return 1

        return 0

    def get_extractor_class(self, argument_wrapper):
        """All the arguments for `SimpleUploadedFile` are strings. So always return a StringExtractor."""
        return StringExtractor

    def get_lookout_kwargs(self):
        """We are searching for the parameters of the init from SimpleUploadFile but want to exclude content_type."""
        return {'cls': SimpleUploadedFile, 'exclude_parameters': ['content_type']}

    def is_valid_search_result(self, search_result):
        """Only allow name and content."""
        if not super().is_valid_search_result(search_result):
            return False

        return search_result in self.ArgumentReferences.get_all()

    def get_default_argument_wrappers(self) -> [ReferenceTokenWrapper]:
        """
        Add some defaults values since content and name are required to create a file. `source_represents_output` is
        set by the parent.
        """
        return [
            ReferenceTokenWrapper(
                token='My content', reference=self.ArgumentReferences.CONTENT),
            ReferenceTokenWrapper(
                token=self.file_variable.token or 'foo', reference=self.ArgumentReferences.NAME)
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

        # get the reference which should be name or content
        reference = extractor.reference
        # ignore GenerationWarnings
        if reference == self.ArgumentReferences.NAME and not extractor.generates_warning:
            # add the file extension to the extracted value
            extracted_value = '{}.{}'.format(extracted_value, self.file_extension_lookout.fittest_keyword or 'txt')

        kwarg = Kwarg(reference, extracted_value)
        expression.add_kwarg(kwarg)
