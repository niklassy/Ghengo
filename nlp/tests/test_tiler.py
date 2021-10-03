import pytest
from django.contrib.auth.models import User

from core.constants import Languages
from django_meta.api import UrlPatternWrapper
from django_meta.model import ExistingModelWrapper
from django_meta.project import DjangoProject
from gherkin.ast import Then
from nlp.converter.model import AssertPreviousModelConverter
from nlp.converter.queryset import ExistsQuerysetConverter, CountQuerysetConverter, ObjectQuerysetConverter
from nlp.converter.response import ResponseConverter, ResponseErrorConverter, ResponseStatusCodeConverter, \
    ManyLengthResponseConverter, ManyCheckEntryResponseConverter
from nlp.generate.argument import Kwarg
from nlp.generate.expression import RequestExpression
from nlp.generate.pytest import PyTestModelFactoryExpression
from nlp.generate.pytest.suite import PyTestTestSuite
from nlp.generate.statement import AssignmentStatement
from nlp.generate.variable import Variable
from nlp.tests.utils import MockTranslator
from nlp.tiler import Tiler, ThenTiler
from settings import Settings


class MockConverter:
    def __init__(self, *args, **kwargs):
        pass


class GoodConverter(MockConverter):
    def get_document_compatibility(self):
        return 1


class BadConverter(MockConverter):
    def get_document_compatibility(self):
        return .2


class AverageConverter(MockConverter):
    def get_document_compatibility(self):
        return .5


def test_tiler_best_converter():
    """Check if the tiler actually returns the best converter."""
    class CustomTiler(Tiler):
        converter_classes = [BadConverter]

    tiler = CustomTiler('Mein Text', Languages.DE, 'django_proj', 'test_case')
    assert isinstance(tiler.best_converter, BadConverter)
    tiler._best_converter = None
    tiler.converter_classes.append(AverageConverter)
    assert isinstance(tiler.best_converter, AverageConverter)
    tiler._best_converter = None
    tiler.converter_classes.append(GoodConverter)
    assert isinstance(tiler.best_converter, GoodConverter)


@pytest.mark.parametrize(
    'keyword, text, expected_converter_cls', [
        ('Dann', 'sollten Aufträge mit dem Namen "Alice" existieren.', ExistsQuerysetConverter),
        ('Dann', 'sollten zwei Aufträge mit dem Namen "Alice" existieren', CountQuerysetConverter),
        ('Dann', 'sollten zwei Benutzer mit dem Namen "Alice" existieren', CountQuerysetConverter),
        ('Dann', 'sollte Alice den Namen "Alice" haben.', AssertPreviousModelConverter),
        ('Dann', 'sollte der Benutzer Alice den Namen "Alice" haben.', AssertPreviousModelConverter),
        ('Dann', 'sollte der Auftrag mit der ID 2 den Namen "Alice" haben.', ObjectQuerysetConverter),
        ('Dann', 'sollte die Antwort den Namen "Alice" enthalten.', ResponseConverter),
        ('Dann', 'sollte der Benutzer den Namen "Alice" enthalten.', ResponseConverter),
        ('Dann', 'sollte der Fehler "asd" enthalten.', ResponseErrorConverter),
        ('Dann', 'sollte die Antwort den Status 200 haben.', ResponseStatusCodeConverter),
        ('Dann', 'sollten drei Einträge zurückgegeben werden.', ManyLengthResponseConverter),
        ('Dann', 'sollten drei Benutzer zurückgegeben werden.', ManyLengthResponseConverter),
        ('Dann', 'sollte die Antwort drei Benutzer enthalten.', ManyLengthResponseConverter),
        ('Dann', 'sollte die Antwort eine Länge von 2 haben.', ManyLengthResponseConverter),
        ('Dann', 'sollte der zweite Eintrag den Namen "Alice" enthalten.', ManyCheckEntryResponseConverter),
    ]
)
def test_then_tiler_best_converter(mocker, keyword, text, expected_converter_cls):
    mocker.patch('deep_translator.GoogleTranslator.translate', MockTranslator())
    suite = PyTestTestSuite('foo')
    test_case = suite.create_and_add_test_case('bar')
    Settings.language = Languages.DE

    test_case.add_statement(AssignmentStatement(
        expression=PyTestModelFactoryExpression(ExistingModelWrapper(User, None), [Kwarg('bar', 123)]),
        variable=Variable('Alice', 'User'),
    ))

    test_case.add_statement(
        AssignmentStatement(
            variable=Variable('response', ''),
            expression=RequestExpression(
                function_name='',
                function_kwargs=[],
                reverse_kwargs=[],
                reverse_name='',
                action_wrapper=UrlPatternWrapper(ExistingModelWrapper.create_with_model(User)),
                client_variable_ref=None,
            )
        )
    )

    tiler = ThenTiler(
        ast_object=Then(keyword=keyword, text=' {}'.format(text)),
        language=Settings.language,
        test_case=test_case,
        django_project=DjangoProject('django_sample_project.apps.config.settings'),
    )

    assert tiler.best_converter.__class__ == expected_converter_cls
