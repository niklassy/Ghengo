from nlp.converter.base_converter import Converter
from nlp.converter.converter import ModelVariableReferenceConverter, ModelFactoryConverter, RequestConverter, \
    FileConverter, CountQuerysetConverter, ExistsQuerysetConverter, ResponseConverter, \
    ManyLengthResponseConverter, ResponseStatusCodeConverter, ResponseErrorConverter, ManyCheckEntryResponseConverter, \
    AssertPreviousModelConverter
from nlp.setup import Nlp


class Tiler(object):
    """
    A tiler class prepares a AST object and converts it into a spacy document. For each tiler you can define
    a list of converters. The tiler will get the Converter that fits the document the best and will get its statements
    and add them to a test case.
    """
    converter_classes: [Converter] = []

    def __init__(self, ast_object, language, django_project, test_case):
        self.ast_object = ast_object
        self.language = language
        self._document = None
        self.django_project = django_project
        self.test_case = test_case
        self._best_converter = None

    @property
    def ast_as_text(self):
        return str(self.ast_object)

    @property
    def document(self):
        if self._document is None:
            self._document = Nlp.for_language(self.language)(self.ast_as_text)
        return self._document

    @property
    def best_converter(self) -> Converter:
        """Returns the converter that fits the document the best."""
        if self._best_converter is None:
            highest_compatibility = 0

            for converter_cls in self.converter_classes:
                converter = converter_cls(self.document, self.ast_object, self.django_project, self.test_case)
                compatibility = converter.get_document_compatibility()

                if compatibility > highest_compatibility:
                    highest_compatibility = compatibility
                    self._best_converter = converter

                    if compatibility >= 1:
                        break

        return self._best_converter

    def add_statements_to_test_case(self):
        statements = self.get_statements()

        for statement in statements:
            self.test_case.add_statement(statement)

    def get_statements(self):
        if not self.best_converter:
            return []

        return self.best_converter.convert_to_statements()


class GivenTiler(Tiler):
    converter_classes = [
        ModelVariableReferenceConverter,
        FileConverter,
        ModelFactoryConverter,
    ]


class WhenTiler(Tiler):
    converter_classes = [RequestConverter]


class ThenTiler(Tiler):
    converter_classes = [
        ManyCheckEntryResponseConverter,
        ManyLengthResponseConverter,
        ResponseStatusCodeConverter,
        ResponseErrorConverter,
        ResponseConverter,
        CountQuerysetConverter,
        AssertPreviousModelConverter,
        ExistsQuerysetConverter,
    ]
