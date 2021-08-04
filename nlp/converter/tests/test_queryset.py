import pytest

from core.constants import Languages
from django_meta.project import DjangoProject
from gherkin.ast import Then, Given
from nlp.converter.queryset import QuerysetConverter, CountQuerysetConverter, ExistsQuerysetConverter, \
    ObjectQuerysetConverter
from nlp.generate.constants import CompareChar
from nlp.generate.expression import ModelQuerysetFilterExpression, ModelQuerysetAllExpression, CompareExpression, \
    ModelQuerysetGetExpression
from nlp.generate.pytest.suite import PyTestTestSuite
from nlp.setup import Nlp
from nlp.tests.utils import MockTranslator


nlp = Nlp.for_language(Languages.DE)
default_doc = nlp('Wenn Alice eine Anfrage macht')
django_project = DjangoProject('django_sample_project.apps.config.settings')


def test_qs_converter(mocker):
    """Check that the QuerysetConverter creates the correct statements."""
    mocker.patch('deep_translator.GoogleTranslator.translate', MockTranslator())
    suite = PyTestTestSuite('foo')
    test_case = suite.create_and_add_test_case('bar')

    # should result in a filter expression
    converter = QuerysetConverter(
        nlp('Dann sollte es zwei Aufträge mit dem Namen Alice geben.'),
        Then(keyword='Dann', text='sollte es zwei Aufträge mit dem Namen Alice geben'),
        django_project,
        test_case,
    )
    statements = converter.convert_to_statements()
    assert len(statements) == 1
    assert isinstance(statements[0].expression, ModelQuerysetFilterExpression)

    # check that a doc without arguments results in an all expression
    converter = QuerysetConverter(
        nlp('Dann sollte es zwei Aufträge geben.'),
        Then(keyword='Dann', text='sollte es zwei Aufträge geben'),
        django_project,
        test_case,
    )
    statements = converter.convert_to_statements()
    assert len(statements) == 1
    assert isinstance(statements[0].expression, ModelQuerysetAllExpression)


def test_qs_count_converter(mocker):
    """Check that the CountQuerysetConverter creates the correct statements."""
    mocker.patch('deep_translator.GoogleTranslator.translate', MockTranslator())
    suite = PyTestTestSuite('foo')
    test_case = suite.create_and_add_test_case('bar')

    # should result in a filter expression
    converter = CountQuerysetConverter(
        nlp('Dann sollte es zwei Aufträge mit dem Namen Alice geben.'),
        Then(keyword='Dann', text='sollte es zwei Aufträge mit dem Namen Alice geben'),
        django_project,
        test_case,
    )
    statements = converter.convert_to_statements()
    assert len(statements) == 2
    assert isinstance(statements[1].expression, CompareExpression)
    assert statements[1].expression.compare_char == CompareChar.EQUAL
    assert statements[1].expression.value_2.value == 2

    # check that a doc without arguments results in an all expression
    converter = CountQuerysetConverter(
        nlp('Dann sollte es zwei oder mehr Aufträge geben.'),
        Then(keyword='Dann', text='sollte es zwei oder mehr Aufträge geben'),
        django_project,
        test_case,
    )
    statements = converter.convert_to_statements()
    assert len(statements) == 2
    assert isinstance(statements[1].expression, CompareExpression)
    assert statements[1].expression.compare_char == CompareChar.GREATER_EQUAL
    assert statements[1].expression.value_2.value == 2


def test_qs_exists_converter(mocker):
    """Check that the ExistsQuerysetConverter creates the correct statements."""
    mocker.patch('deep_translator.GoogleTranslator.translate', MockTranslator())
    suite = PyTestTestSuite('foo')
    test_case = suite.create_and_add_test_case('bar')

    # should result in a filter expression
    converter = ExistsQuerysetConverter(
        nlp('Dann sollte es zwei Aufträge mit dem Namen Alice geben.'),
        Then(keyword='Dann', text='sollte es zwei Aufträge mit dem Namen Alice geben'),
        django_project,
        test_case,
    )
    statements = converter.convert_to_statements()
    assert len(statements) == 2
    assert isinstance(statements[0].expression, ModelQuerysetFilterExpression)
    assert str(statements[1]) == 'assert qs_0.exists()'

    for s in statements:
        test_case.add_statement(s)

    # check that a doc without arguments results in an all expression
    converter = ExistsQuerysetConverter(
        nlp('Dann sollte es zwei oder mehr Aufträge geben.'),
        Then(keyword='Dann', text='sollte es zwei oder mehr Aufträge geben'),
        django_project,
        test_case,
    )
    statements = converter.convert_to_statements()
    assert len(statements) == 2
    assert isinstance(statements[0].expression, ModelQuerysetAllExpression)
    assert str(statements[1]) == 'assert qs_1.exists()'



@pytest.mark.parametrize(
    'doc, min_compatibility, max_compatibility', [
        (nlp('Dann sollte der Auftrag mit der ID 1 den Namen "Alice" haben.'), 0.7, 1),
        (nlp('Dann sollte das ToDo mit dem Namen "Asd" den Titel "Blubb" haben.'), 0.7, 1),
        (nlp('Dann sollte ein Auftrag existieren.'), 0, 0.3),
        (nlp('Dann sollten Aufträge mit dem Namen "QWE" existieren.'), 0, 0.3),
        (nlp('Dann sollte es einen Fehler "error" geben.'), 0, 0.3),
    ]
)
def test_object_qs_converter_compatibility(doc, min_compatibility, max_compatibility, mocker):
    """Check that the ObjectQuerysetConverter detects the compatibility of different documents correctly."""
    mocker.patch('deep_translator.GoogleTranslator.translate', MockTranslator())
    suite = PyTestTestSuite('foo')
    test_case = suite.create_and_add_test_case('bar')

    converter = ObjectQuerysetConverter(
        doc,
        Given(keyword='Gegeben sei', text='ein Auftrag mit der Nummer 3'),
        django_project,
        test_case,
    )
    assert converter.get_document_compatibility() >= min_compatibility
    assert converter.get_document_compatibility() <= max_compatibility


@pytest.mark.parametrize(
    'doc, filter_fields, assert_field', [
        (nlp('Dann sollte der Auftrag mit der ID 1 den Namen "Alice" haben.'), ['id'], 'name'),
        (nlp('Dann sollte das ToDo mit dem System 1 den Titel "Blubb" haben.'), ['system'], 'title'),
        (
            nlp('Dann sollte der Auftrag mit der ID 1 und dem Namen "Alice" den Wert "Test" haben.'),
            ['id', 'name'],
            'worth'
        ),
    ]
)
def test_object_qs_converter_output(doc, mocker, filter_fields, assert_field):
    """Check that the output of ObjectQuerysetConverter is correct."""
    mocker.patch('deep_translator.GoogleTranslator.translate', MockTranslator())
    suite = PyTestTestSuite('foo')
    test_case = suite.create_and_add_test_case('bar')

    converter = ObjectQuerysetConverter(
        doc,
        Given(keyword='Gegeben sei', text='ein Auftrag mit der Nummer 3'),
        django_project,
        test_case,
    )
    statements = converter.convert_to_statements()
    assert len(statements) == 2

    # check the filter statement
    assert isinstance(statements[0].expression, ModelQuerysetGetExpression)
    for i, filter_field_name in enumerate(filter_fields):
        assert statements[0].expression.function_kwargs[i].name == filter_field_name

    # check the assert statement
    assert isinstance(statements[1].expression, CompareExpression)
    assert statements[1].expression.value_1.attribute_name == assert_field


