import pytest
from django.contrib.auth.models import User

from core.constants import Languages
from django_meta.model import ExistingModelWrapper
from django_meta.project import DjangoProject
from django_sample_project.apps.order.models import Order
from gherkin.ast import Given, TableCell, TableRow, DataTable
from nlp.converter.model import AssertPreviousModelConverter, ModelFactoryConverter, ModelVariableReferenceConverter
from nlp.generate.argument import Kwarg
from nlp.generate.expression import ModelSaveExpression
from nlp.generate.pytest import PyTestModelFactoryExpression
from nlp.generate.pytest.suite import PyTestTestSuite
from nlp.generate.statement import AssignmentStatement, ModelFieldAssignmentStatement
from nlp.generate.variable import Variable
from nlp.setup import Nlp
from nlp.tests.utils import MockTranslator

nlp = Nlp.for_language(Languages.DE)
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
    mocker.patch('deep_translator.GoogleTranslator.translate', MockTranslator())
    suite = PyTestTestSuite('foo')
    test_case = suite.create_and_add_test_case('bar')
    converter = ModelFactoryConverter(
        doc,
        Given(keyword='Gegeben sei', text='ein Auftrag mit der Nummer 3'),
        django_project,
        test_case,
    )
    assert converter.get_document_compatibility() >= min_compatibility
    assert converter.get_document_compatibility() <= max_compatibility


@pytest.mark.parametrize(
    'doc, expected_field_names', [
        (nlp('Gegeben sei ein Auftrag mit der Nummer 3'), ['number']),
        (nlp('Gegeben sei ein Auftrag mit der Nummer 3 und "Fertig" als Status'), ['number', 'status']),
        (nlp('Gegeben sei ein Dach mit der Länge 3'), ['length']),
        (nlp('Gegeben sei ein ToDo Alice als Besitzerin'), ['owner']),
        (nlp('Gegeben sei ein ToDo, das nicht aus dem anderen System kommt'), ['from_other_system']),
        (
            nlp('Gegeben sei ein ToDo, das nicht aus dem anderen System kommt und System 4'),
            ['from_other_system', 'system'],
        ),
        (
            nlp('Gegeben sei ein Benutzer Alice mit dem Benutzernamen Alice und "Haus1234" als Passwort'),
            ['username', 'password'],
        ),
    ]
)
def test_model_factory_converter_extractors(doc, expected_field_names, mocker):
    """Check that the correct amount of extractors for the correct fields are determined from the input."""
    mocker.patch('deep_translator.GoogleTranslator.translate', MockTranslator())
    suite = PyTestTestSuite('foo')
    test_case = suite.create_and_add_test_case('bar')
    converter = ModelFactoryConverter(
        doc,
        Given(keyword='Gegeben sei', text='ein Auftrag mit der Nummer 3'),
        django_project,
        test_case,
    )
    converter.prepare_converter()
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
    mocker.patch('deep_translator.GoogleTranslator.translate', MockTranslator())
    suite = PyTestTestSuite('foo')
    test_case = suite.create_and_add_test_case('bar')
    converter = ModelFactoryConverter(
        doc,
        Given(keyword='Gegeben sei', text='ein Auftrag mit der Nummer 3'),
        django_project,
        test_case,
    )
    assert str(converter.model.token) == expected_model_token_text


@pytest.mark.parametrize(
    'doc, expected_variable_name', [
        (nlp('Gegeben sei ein Auftrag 1'), '1'),
        (nlp('Und ein Benutzer Alice'), 'alice'),
        (nlp('Gegeben sei ein Benutzer Alice'), 'alice'),
        (nlp('Gegeben sei ein Benutzer Bob'), 'bob'),
        (nlp('Und eine Inventur von 2004'), ''),
        (nlp('Und ein Dach mit einer Länge von 3'), ''),
        (nlp('Und ein Dach "MeinDach1" mit einer Länge von 3'), 'mein_dach1'),
    ]
)
def test_model_factory_converter_variable_name(doc, expected_variable_name, mocker):
    """Check that the correct variable name is extracted."""
    mocker.patch('deep_translator.GoogleTranslator.translate', MockTranslator())
    suite = PyTestTestSuite('foo')
    test_case = suite.create_and_add_test_case('bar')
    converter = ModelFactoryConverter(
        doc,
        Given(keyword='Gegeben sei', text='ein Auftrag mit der Nummer 3'),
        django_project,
        test_case,
    )
    assert str(converter.variable.name) == expected_variable_name


def test_model_factory_converter_datatable(mocker):
    """Check that statements are correctly generated in the case GIVEN has a datatable."""
    mocker.patch('deep_translator.GoogleTranslator.translate', MockTranslator())
    header = TableRow([TableCell('number'), TableCell('value'), TableCell('name')])
    row_1 = TableRow([TableCell(123), TableCell('val_1'), TableCell('name_2')])
    row_2 = TableRow([TableCell(234), TableCell('val_2'), TableCell('name_3')])
    rows = [row_1, row_2]
    datatable = DataTable(header=header, rows=rows)
    given = Given(keyword='Gegeben sei', text='ein Auftrag mit der Nummer 3', argument=datatable)
    suite = PyTestTestSuite('foo')
    test_case = suite.create_and_add_test_case('bar')
    converter = ModelFactoryConverter(nlp('Gegeben sei ein Auftrag'), given, django_project, test_case)
    statements = converter.convert_to_statements()
    assert len(statements) == 2

    for statement_index, statement in enumerate(statements):
        for kwarg_index, kwarg in enumerate(statement.expression.function_kwargs):
            assert kwarg.name == header.cells[kwarg_index].value
            assert kwarg.value.value == rows[statement_index].cells[kwarg_index].value


@pytest.mark.parametrize(
    'doc, min_compatibility, max_compatibility', [
        (nlp('Dann sollte Alice den Nachnamen "Alice" und den Vornamen "Alice" haben.'), 0.7, 1),
        (nlp('Dann sollte der Auftrag 1 den Namen "Alice" haben.'), 0.7, 1),
        (nlp('Dann sollte Alice den Nachnamen "Alice" haben.'), 0.7, 1),
        (nlp('Dann sollte Bob den Nachnamen "Alice" haben.'), 0, 0.3),
        (nlp('Dann sollte das ToDo mit dem Namen "Asd" den Titel "Blubb" haben.'), 0, 0.3),
        (nlp('Dann sollte die Antwort existieren'), 0, 0.3),
    ]
)
def test_object_qs_converter_compatibility(doc, min_compatibility, max_compatibility, mocker):
    """Check that the AssertPreviousModelConverter detects the compatibility of different documents correctly."""
    mocker.patch('deep_translator.GoogleTranslator.translate', MockTranslator())
    suite = PyTestTestSuite('foo')
    test_case = suite.create_and_add_test_case('bar')

    # add two statements: a user `alice` and an `order_1`
    test_case.add_statement(AssignmentStatement(
        expression=PyTestModelFactoryExpression(ExistingModelWrapper(User, None), [Kwarg('bar', 123)]),
        variable=Variable('Alice', 'User'),     # <- variable name is Alice
    ))
    test_case.add_statement(AssignmentStatement(
        expression=PyTestModelFactoryExpression(ExistingModelWrapper(Order, None), [Kwarg('bar', 123)]),
        variable=Variable('1', 'Order'),
    ))

    converter = AssertPreviousModelConverter(
        doc,
        Given(keyword='Gegeben sei', text='ein Auftrag mit der Nummer 3'),
        django_project,
        test_case,
    )
    assert converter.get_document_compatibility() >= min_compatibility
    assert converter.get_document_compatibility() <= max_compatibility


@pytest.mark.parametrize(
    'doc, filter_fields, variable_type', [
        (nlp('Dann sollte Alice den Namen "Alice" haben.'), ['first_name'], 'user'),
        (nlp('Dann sollte der Benutzer 1 den Namen "Alice" haben.'), ['first_name'], 'user_no_name'),
        (nlp('Dann sollte der Auftrag 1 den Namen "Alice" haben.'), ['name'], 'order'),
        (nlp('Dann sollte der Auftrag 1 den Namen "Alice" und den Wert "Test" haben.'), ['name', 'worth'], 'order'),
    ]
)
def test_object_qs_converter_output(doc, mocker, filter_fields, variable_type):
    """Check that the output of AssertPreviousModelConverter is correct."""
    assert variable_type in ['order', 'user', 'user_no_name', None]

    mocker.patch('deep_translator.GoogleTranslator.translate', MockTranslator())
    suite = PyTestTestSuite('foo')
    test_case = suite.create_and_add_test_case('bar')

    # add two statements: a user `alice` and an `order_1`
    user_variable = Variable('Alice', 'User')
    user_no_name_variable = Variable('1', 'User')
    order_variable = Variable('1', 'Order')

    if variable_type == 'user':
        referenced_variable = user_variable
    elif variable_type == 'order':
        referenced_variable = order_variable
    elif variable_type == 'user_no_name':
        referenced_variable = user_no_name_variable
    else:
        referenced_variable = None

    test_case.add_statement(AssignmentStatement(
        expression=PyTestModelFactoryExpression(ExistingModelWrapper(Order, None), []),
        variable=order_variable,
    ))
    test_case.add_statement(AssignmentStatement(
        expression=PyTestModelFactoryExpression(ExistingModelWrapper(User, None), []),
        variable=user_variable,
    ))
    test_case.add_statement(AssignmentStatement(
        expression=PyTestModelFactoryExpression(ExistingModelWrapper(User, None), []),
        variable=user_no_name_variable,
    ))

    converter = AssertPreviousModelConverter(
        doc,
        Given(keyword='Gegeben sei', text='ein Auftrag mit der Nummer 3'),
        django_project,
        test_case,
    )
    statements = converter.convert_to_statements()
    assert len(statements) == len(filter_fields) + 1
    assert 'refresh_from_db' in statements[0].expression.to_template()

    for i, filter_field_name in enumerate(filter_fields):
        statement = statements[i + 1]
        exp = statement.expression

        assert exp.value_1.attribute_name == filter_field_name

        if referenced_variable:
            assert exp.value_1.variable_ref == referenced_variable


def test_model_variable_reference_converter(mocker):
    """Check that the ModelVariableReferenceConverter correctly creates statements to modify an object."""
    mocker.patch('deep_translator.GoogleTranslator.translate', MockTranslator())
    given = Given(keyword='Und', text='Alice erhält das Passwort "Haus123"')
    suite = PyTestTestSuite('foo')
    test_case = suite.create_and_add_test_case('bar')
    test_case.add_statement(AssignmentStatement(
        expression=PyTestModelFactoryExpression(ExistingModelWrapper(User, None), [Kwarg('bar', 123)]),
        variable=Variable('Alice', 'User'),  # <-- variable defined
    ))
    converter = ModelVariableReferenceConverter(
        nlp('Und Alice erhält das Passwort "Haus123"'), given, django_project, test_case)
    statements = converter.convert_to_statements()
    assert len(statements) == 2     # modify statement and save statement
    assert isinstance(statements[0], ModelFieldAssignmentStatement)
    assert isinstance(statements[1].expression, ModelSaveExpression)


def test_model_variable_reference_converter_multiple_name(mocker):
    """
    Check that the ModelVariableReferenceConverter handles when two model instances are named the same but relate
    to different models.
    """
    mocker.patch('deep_translator.GoogleTranslator.translate', MockTranslator())
    given = Given(keyword='Und', text='Alice erhält das Passwort "Haus123"')
    suite = PyTestTestSuite('foo')
    test_case = suite.create_and_add_test_case('bar')
    user_variable = Variable('1', 'User')
    test_case.add_statement(AssignmentStatement(
        expression=PyTestModelFactoryExpression(ExistingModelWrapper(User, None), [Kwarg('bar', 123)]),
        variable=user_variable,
    ))
    test_case.add_statement(AssignmentStatement(
        expression=PyTestModelFactoryExpression(ExistingModelWrapper(Order, None), [Kwarg('bar', 123)]),
        variable=Variable('1', 'Order'),
    ))
    converter = ModelVariableReferenceConverter(
        nlp('Und Benutzer 1 erhält das Passwort "Haus123"'), given, django_project, test_case)
    statements = converter.convert_to_statements()

    assert len(statements) == 2
    assert isinstance(statements[0], ModelFieldAssignmentStatement)
    assert isinstance(statements[1].expression, ModelSaveExpression)
    assert isinstance(converter.model.value, ExistingModelWrapper)
    assert converter.model.value.model == User
    assert converter.variable_ref.value == user_variable


@pytest.mark.parametrize(
    'doc, variable, model_wrapper, min_compatibility, max_compatibility', [
        (nlp('Und Benutzer 1 erhält das Passwort "Test"'), Variable('1', 'User'), ExistingModelWrapper(User, None), 0.7, 1),
        # no previous statement
        (nlp('Und Benutzer 1 erhält das Passwort "Test"'), None, None, 0, 0.1),
        # wrong model
        (nlp('Und Benutzer 1 erhält das Passwort "Test"'), Variable('1', 'User'), ExistingModelWrapper(Order, None), 0, 0.1),
        # wrong input
        (nlp('Gegeben sei ein Benutzer Alice'), Variable('1', 'User'), ExistingModelWrapper(User, None), 0, 0.1),
        (nlp('Wenn ein Auftrag erstellt wird'), Variable('1', 'User'), ExistingModelWrapper(User, None), 0, 0.1),
        (nlp('Und ein Auftrag mit der Nummer 2'), Variable('1', 'Order'), ExistingModelWrapper(Order, None), 0, 0.1),
    ]
)
def test_model_variable_converter_compatibility(
    doc,
    variable,
    model_wrapper,
    min_compatibility,
    max_compatibility,
    mocker,
):
    """Check that the ModelVariableReferenceConverter detects the compatibility of different documents correctly."""
    mocker.patch('deep_translator.GoogleTranslator.translate', MockTranslator())
    suite = PyTestTestSuite('foo')
    test_case = suite.create_and_add_test_case('bar')
    if variable and model_wrapper:
        test_case.add_statement(AssignmentStatement(
            expression=PyTestModelFactoryExpression(model_wrapper, [Kwarg('bar', 123)]),
            variable=variable,
        ))
    converter = ModelVariableReferenceConverter(
        doc,
        Given(keyword='Und', text='der Auftrag 3 hat das Passwort 3.'),
        django_project,
        test_case,
    )
    assert converter.get_document_compatibility() >= min_compatibility
    assert converter.get_document_compatibility() <= max_compatibility

