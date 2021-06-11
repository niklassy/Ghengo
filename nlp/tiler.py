from nlp.converter import ModelFactoryConverter, Converter
from nlp.setup import Nlp


class Tiler(object):
    """
    A tiler class prepares a AST object and converts it into a spacy document. For each tiler you can define
    a list of converters. The tiler will get the Converter that fits the document the best and will get its statements
    and add them to a test case.
    """
    converter_classes: [Converter] = []

    def __init__(self, ast_object, language, django_project):
        self.ast_object = ast_object
        self.language = language
        self._document = None
        self.django_project = django_project
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
        if self._best_converter is None:
            highest_fitness = 0

            for converter_cls in self.converter_classes:
                converter = converter_cls(self.document, self.ast_object, self.django_project)
                fitness = converter.get_document_fitness()

                if fitness > highest_fitness:
                    highest_fitness = fitness
                    self._best_converter = converter

        return self._best_converter

    def add_statements_to_test_case(self, test_case):
        statements = self.get_statements(test_case)

        for statement in statements:
            test_case.add_statement(statement)

    def get_statements(self, test_case):
        return self.best_converter.convert_to_statements(test_case)


class GivenTiler(Tiler):
    converter_classes = [ModelFactoryConverter]
