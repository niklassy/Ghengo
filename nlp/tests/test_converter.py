import pytest

from django_meta.project import DjangoProject
from gherkin.ast import Given, DataTable, TableRow, TableCell
from nlp.converter import ModelFactoryConverter
from nlp.generate.pytest.suite import PyTestTestSuite
from nlp.setup import Nlp
from nlp.tests.utils import MockTranslator

nlp = Nlp.for_language('de')
default_doc = nlp('Wenn Alice eine Anfrage macht')
django_project = DjangoProject('django_sample_project.apps.config.settings')


@pytest.mark.parametrize(
    'doc, min_compatibility, max_compatibility', [
        (nlp('Gegeben sei ein Auftrag'), 0.7, 1),
        (nlp('Und ein Benutzer Alice'), 0.7, 1),
        (nlp('Und eine Inventur von 2004'), 0.7, 1),
        (nlp('Wenn Alice eine Anfrage macht'), 0, 0.1),
        (nlp('Und Alice eine weitere Anfrage macht'), 0, 0.1),
        (nlp('Sie sollten lieber Zuhause bleiben'), 0, 0.1),
        (nlp('Dann sollte Alice keinen Auftrag mehr haben'), 0, 0.1),
        (nlp('Und der Auftrag sollte nicht mehr existieren '), 0.3, 0.5),
    ]
)
def test_model_factory_converter_compatibility(doc, min_compatibility, max_compatibility, mocker):
    """Check that the ModelFactoryConverter detects the compatibility of different documents correctly."""
    suite = PyTestTestSuite('foo')
    test_case = suite.create_and_add_test_case('bar')
    converter = ModelFactoryConverter(
        doc,
        Given(keyword='Gegeben sei', text='ein Auftrag mit der Nummer 3'),
        django_project,
        test_case,
    )
    mocker.patch('deep_translator.GoogleTranslator.translate', MockTranslator())
    assert converter.get_document_compatibility() >= min_compatibility
    assert converter.get_document_compatibility() <= max_compatibility


@pytest.mark.parametrize(
    'doc, expected_field_names', [
        # (nlp('Gegeben sei ein Auftrag mit der Nummer 3'), ['number']),
        # (nlp('Gegeben sei ein Auftrag mit der Nummer 3 und "Fertig" als Status'), ['number', 'status']),
        # (nlp('Gegeben sei ein Dach mit der Länge 3'), ['length']),
        # (nlp('Gegeben sei ein ToDo Alice als Besitzerin'), ['owner']),
        (nlp('Gegeben sei ein ToDo, das nicht aus dem anderen System kommt'), ['from_other_system']),
        (
            nlp('Gegeben sei ein ToDo, das nicht aus dem anderen System kommt und System 4'),
            ['from_other_system', 'system'],
        ),
        (
            nlp('Gegeben ein Benutzer Alice mit dem Benutzernamen Alice und "Haus1234" als Passwort'),
            ['username', 'password'],
        ),
    ]
)
def test_model_factory_converter_extractors(doc, expected_field_names, mocker):
    """Check that the correct amount of extractors for the correct fields are determined from the input."""
    suite = PyTestTestSuite('foo')
    test_case = suite.create_and_add_test_case('bar')
    converter = ModelFactoryConverter(
        doc,
        Given(keyword='Gegeben sei', text='ein Auftrag mit der Nummer 3'),
        django_project,
        test_case,
    )
    mocker.patch('deep_translator.GoogleTranslator.translate', MockTranslator())
    assert len(converter.extractors) == len(expected_field_names), '{} != {}'.format(
        [e.field_name for e in converter.extractors], expected_field_names)
    for index, extractor in enumerate(converter.extractors):
        assert extractor.field_name == expected_field_names[index]


@pytest.mark.parametrize(
    'doc, expected_model_token_text', [
        (nlp('Gegeben sei ein Auftrag'), 'Auftrag'),
        (nlp('Und ein Benutzer Alice'), 'Benutzer'),
        (nlp('Gegeben sei ein Benutzer Alice'), 'Benutzer'),
        (nlp('Gegeben sei ein Benutzer Bob'), 'Benutzer'),
        (nlp('Und eine Inventur von 2004'), 'Inventur'),
        (nlp('Und ein Dach mit einer Länge von 3'), 'Dach'),
    ]
)
def test_model_factory_converter_model_token(doc, expected_model_token_text, mocker):
    """Check if the model is correctly extracted."""
    suite = PyTestTestSuite('foo')
    test_case = suite.create_and_add_test_case('bar')
    converter = ModelFactoryConverter(
        doc,
        Given(keyword='Gegeben sei', text='ein Auftrag mit der Nummer 3'),
        django_project,
        test_case,
    )
    mocker.patch('deep_translator.GoogleTranslator.translate', MockTranslator())
    assert str(converter.model_token) == expected_model_token_text


@pytest.mark.parametrize(
    'doc, expected_variable_name', [
        (nlp('Gegeben sei ein Auftrag 1'), '1'),
        (nlp('Und ein Benutzer Alice'), 'alice'),
        (nlp('Gegeben sei ein Benutzer Alice'), 'alice'),
        (nlp('Gegeben sei ein Benutzer Bob'), 'bob'),
        (nlp('Und eine Inventur von 2004'), ''),
        (nlp('Und ein Dach mit einer Länge von 3'), ''),
        (nlp('Und ein Dach MeinDach1 mit einer Länge von 3'), 'mein_dach1'),
    ]
)
def test_model_factory_converter_variable_name(doc, expected_variable_name, mocker):
    """Check that the correct variable name is extracted."""
    suite = PyTestTestSuite('foo')
    test_case = suite.create_and_add_test_case('bar')
    converter = ModelFactoryConverter(
        doc,
        Given(keyword='Gegeben sei', text='ein Auftrag mit der Nummer 3'),
        django_project,
        test_case,
    )
    mocker.patch('deep_translator.GoogleTranslator.translate', MockTranslator())
    assert str(converter.variable_name) == expected_variable_name


def test_model_factory_converter_datatable(mocker):
    """Check that statements are correctly generated in the case GIVEN has a datatable."""
    header = TableRow([TableCell('number'), TableCell('value'), TableCell('name')])
    row_1 = TableRow([TableCell(123), TableCell('val_1'), TableCell('name_2')])
    row_2 = TableRow([TableCell(234), TableCell('val_2'), TableCell('name_3')])
    rows = [row_1, row_2]
    datatable = DataTable(header=header, rows=rows)
    given = Given(keyword='Gegeben sei', text='ein Auftrag mit der Nummer 3', argument=datatable)
    suite = PyTestTestSuite('foo')
    test_case = suite.create_and_add_test_case('bar')
    converter = ModelFactoryConverter(nlp('Gegeben sei ein Auftrag'), given, django_project, test_case)
    mocker.patch('deep_translator.GoogleTranslator.translate', MockTranslator())
    statements = converter.convert_to_statements()
    assert len(statements) == 2

    for statement_index, statement in enumerate(statements):
        for kwarg_index, kwarg in enumerate(statement.expression.function_kwargs):
            assert kwarg.name == header.cells[kwarg_index].value
            assert kwarg.value.value == rows[statement_index].cells[kwarg_index].value

