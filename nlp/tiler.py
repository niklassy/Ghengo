from core.performance import AveragePerformanceMeasurement
from nlp.converter.base.converter import Converter
from nlp.converter.file import FileConverter
from nlp.converter.model import ModelVariableReferenceConverter, ModelFactoryConverter, AssertPreviousModelConverter
from nlp.converter.queryset import CountQuerysetConverter, ObjectQuerysetConverter, ExistsQuerysetConverter
from nlp.converter.request import RequestConverter
from nlp.converter.response import ManyCheckEntryResponseConverter, ManyLengthResponseConverter, \
    ResponseStatusCodeConverter, ResponseErrorConverter, ResponseConverter
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
            try:
                ast_name = self.ast_object.get_parent_step().__class__.__name__
            except AttributeError:
                ast_name = 'foo'
            measure_key = '------- FIND_BEST_CONVERTER_{}'.format(ast_name)
            AveragePerformanceMeasurement.start_measure(measure_key)
            highest_compatibility = 0

            for converter_cls in self.converter_classes:
                converter = converter_cls(self.document, self.ast_object, self.django_project, self.test_case)
                compatibility = converter.get_document_compatibility()

                if compatibility > highest_compatibility:
                    highest_compatibility = compatibility
                    self._best_converter = converter

                    if compatibility >= 1:
                        break

            AveragePerformanceMeasurement.end_measure(measure_key)
        return self._best_converter

    def add_statements_to_test_case(self):
        statements = self.get_statements()

        for statement in statements:
            self.test_case.add_statement(statement)

    def get_statements(self):
        if not self.best_converter:
            return []

        measure_key = '------- GET_STATEMENTS_{}'.format(self.ast_object.get_parent_step().__class__.__name__)
        AveragePerformanceMeasurement.start_measure(measure_key)
        output = self.best_converter.convert_to_statements()
        AveragePerformanceMeasurement.end_measure(measure_key)
        return output


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
        ObjectQuerysetConverter,
        ExistsQuerysetConverter,
    ]
