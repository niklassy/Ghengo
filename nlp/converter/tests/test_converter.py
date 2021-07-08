import pytest
from django.contrib.auth.models import User

from django_meta.model import ModelAdapter
from django_meta.project import DjangoProject
from django_sample_project.apps.order.models import Order
from gherkin.ast import Given, DataTable, TableRow, TableCell
from nlp.converter.converter import ModelFactoryConverter, ModelVariableReferenceConverter, RequestConverter
from nlp.generate.argument import Kwarg
from nlp.generate.expression import ModelSaveExpression, APIClientExpression, RequestExpression, \
    APIClientAuthenticateExpression
from nlp.generate.pytest import PyTestModelFactoryExpression
from nlp.generate.pytest.suite import PyTestTestSuite
from nlp.generate.statement import AssignmentStatement, ModelFieldAssignmentStatement
from nlp.generate.variable import Variable
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
    assert str(converter.model.token) == expected_model_token_text


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
    assert str(converter.variable.name) == expected_variable_name


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


def test_model_variable_reference_converter():
    """Check that the ModelVariableReferenceConverter correctly creates statements to modify an object."""
    given = Given(keyword='Und', text='Alice erhält das Passwort "Haus123"')
    suite = PyTestTestSuite('foo')
    test_case = suite.create_and_add_test_case('bar')
    test_case.add_statement(AssignmentStatement(
        expression=PyTestModelFactoryExpression(ModelAdapter(User, None), [Kwarg('bar', 123)]),
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
    given = Given(keyword='Und', text='Alice erhält das Passwort "Haus123"')
    suite = PyTestTestSuite('foo')
    mocker.patch('deep_translator.GoogleTranslator.translate', MockTranslator())
    test_case = suite.create_and_add_test_case('bar')
    user_variable = Variable('1', 'User')
    test_case.add_statement(AssignmentStatement(
        expression=PyTestModelFactoryExpression(ModelAdapter(User, None), [Kwarg('bar', 123)]),
        variable=user_variable,
    ))
    test_case.add_statement(AssignmentStatement(
        expression=PyTestModelFactoryExpression(ModelAdapter(Order, None), [Kwarg('bar', 123)]),
        variable=Variable('1', 'Order'),
    ))
    converter = ModelVariableReferenceConverter(
        nlp('Und Benutzer 1 erhält das Passwort "Haus123"'), given, django_project, test_case)
    statements = converter.convert_to_statements()

    assert len(statements) == 2
    assert isinstance(statements[0], ModelFieldAssignmentStatement)
    assert isinstance(statements[1].expression, ModelSaveExpression)
    assert isinstance(converter.model.value, ModelAdapter)
    assert converter.model.value.model == User
    assert converter.variable.value == user_variable


@pytest.mark.parametrize(
    'doc, variable, model_adapter, min_compatibility, max_compatibility', [
        (nlp('Und Benutzer 1 erhält das Passwort "Test"'), Variable('1', 'User'), ModelAdapter(User, None), 0.7, 1),
        # no previous statement
        (nlp('Und Benutzer 1 erhält das Passwort "Test"'), None, None, 0, 0.1),
        # wrong model
        (nlp('Und Benutzer 1 erhält das Passwort "Test"'), Variable('1', 'User'), ModelAdapter(Order, None), 0, 0.1),
        # wrong input
        (nlp('Gegeben sei ein Benutzer Alice'), Variable('1', 'User'), ModelAdapter(User, None), 0, 0.1),
        (nlp('Wenn ein Auftrag erstellt wird'), Variable('1', 'User'), ModelAdapter(User, None), 0, 0.1),
        (nlp('Und ein Auftrag mit der Nummer 2'), Variable('1', 'Order'), ModelAdapter(Order, None), 0, 0.1),
    ]
)
def test_model_variable_converter_compatibility(
    doc,
    variable,
    model_adapter,
    min_compatibility,
    max_compatibility,
    mocker,
):
    """Check that the ModelVariableReferenceConverter detects the compatibility of different documents correctly."""
    suite = PyTestTestSuite('foo')
    test_case = suite.create_and_add_test_case('bar')
    if variable and model_adapter:
        test_case.add_statement(AssignmentStatement(
            expression=PyTestModelFactoryExpression(model_adapter, [Kwarg('bar', 123)]),
            variable=variable,
        ))
    converter = ModelVariableReferenceConverter(
        doc,
        Given(keyword='Und', text='der Auftrag 3 hat das Passwort 3.'),
        django_project,
        test_case,
    )
    mocker.patch('deep_translator.GoogleTranslator.translate', MockTranslator())
    assert converter.get_document_compatibility() >= min_compatibility
    assert converter.get_document_compatibility() <= max_compatibility


def test_model_request_converter(mocker):
    """Check that the RequestConverter correctly creates statements to send requests."""
    given = Given(keyword='Wenn', text='Alice einen Auftrag holt')
    suite = PyTestTestSuite('foo')
    mocker.patch('deep_translator.GoogleTranslator.translate', MockTranslator())
    test_case = suite.create_and_add_test_case('bar')
    test_case.add_statement(AssignmentStatement(
        expression=PyTestModelFactoryExpression(ModelAdapter(User, None), [Kwarg('bar', 123)]),
        variable=Variable('Alice', 'User'),  # <-- variable defined
    ))
    converter = RequestConverter(nlp('Wenn Alice einen Auftrag holt'), given, django_project, test_case)
    statements = converter.convert_to_statements()
    assert converter.from_anonymous_user is False
    assert len(statements) == 3     # client + authenticate + request

    for s in statements:
        test_case.add_statement(s)

    converter = RequestConverter(nlp('Wenn Alice einen Auftrag holt'), given, django_project, test_case)
    statements = converter.convert_to_statements()
    assert len(statements) == 2     # client already exists; so authenticate + request


def test_model_request_converter_anonymous(mocker):
    """Check that the RequestConverter correctly creates statements to send requests from an anonymous user."""
    given = Given(keyword='Wenn', text='Alice einen Auftrag holt')
    suite = PyTestTestSuite('foo')
    mocker.patch('deep_translator.GoogleTranslator.translate', MockTranslator())
    test_case = suite.create_and_add_test_case('bar')
    test_case.add_statement(AssignmentStatement(
        expression=PyTestModelFactoryExpression(ModelAdapter(User, None), [Kwarg('bar', 123)]),
        variable=Variable('Alice', 'User'),  # <-- variable defined
    ))
    converter = RequestConverter(nlp('Wenn ein Auftrag erstellt wird'), given, django_project, test_case)
    statements = converter.convert_to_statements()
    assert len(statements) == 2     # client  + request
    assert converter.from_anonymous_user is True
    assert isinstance(statements[0].expression, APIClientExpression)
    assert isinstance(statements[1].expression, RequestExpression)


def test_model_request_converter_with_reference(mocker):
    """Check that a converter with a reference to a model sets all properties correctly and has the correct output."""
    given = Given(keyword='Wenn', text='Alice einen Auftrag holt')
    suite = PyTestTestSuite('foo')
    mocker.patch('deep_translator.GoogleTranslator.translate', MockTranslator())
    test_case = suite.create_and_add_test_case('bar')
    test_case.add_statement(AssignmentStatement(
        expression=PyTestModelFactoryExpression(ModelAdapter(User, None), []),
        variable=Variable('Alice', 'User'),
    ))
    order_variable = Variable('1', 'Order')
    test_case.add_statement(AssignmentStatement(
        expression=PyTestModelFactoryExpression(ModelAdapter(Order, None), []),
        variable=order_variable,
    ))
    doc = nlp('Wenn Alice den Auftrag 1 löscht')
    converter = RequestConverter(doc, given, django_project, test_case)
    statements = converter.convert_to_statements()

    # check all the properties
    assert isinstance(converter.model.value, ModelAdapter)
    assert converter.model.value.model == Order
    assert converter.model.token == doc[3]
    assert converter.model_variable.value == order_variable
    assert converter.model_variable.token == doc[4]
    assert converter.user.token == doc[1]

    assert len(statements) == 3
    assert isinstance(statements[0].expression, APIClientExpression)
    assert isinstance(statements[1].expression, APIClientAuthenticateExpression)
    assert isinstance(statements[2].expression, RequestExpression)
    # check that the reverse expression holds the data of the order variable
    reverse_kwargs = statements[2].expression.reverse_expression.function_kwargs
    attribute = reverse_kwargs[0].value.value
    assert attribute.variable == order_variable


@pytest.mark.parametrize(
    'doc, min_compatibility, max_compatibility', [
        (nlp('Wenn ein Auftrag erstellt wird'), 0.7, 1),
        (nlp('Wenn ein Auftrag mit dem Namen "Test" und der Nummer 3 erstellt wird'), 0.7, 1),
        (nlp('Wenn ein Auftrag geändert wird'), 0.7, 1),
        (nlp('Wenn ein Auftrag aktualisiert wird'), 0.7, 1),
        (nlp('Wenn die Liste der Aufträge geholt wird'), 0.7, 1),
        (nlp('Wenn die ein Auftrag gelöscht wird'), 0.7, 1),
        (nlp('Wenn Alice einen Auftrag erstellt'), 0.7, 1),
        (nlp('Gegeben sei ein Auftrag'), 0, 0.1),
        (nlp('Und ein Benutzer Alice'), 0, 0.1),
        (nlp('Sie fahren mit dem Auto'), 0, 0.1),
    ]
)
def test_model_request_converter_compatibility(doc, min_compatibility, max_compatibility, mocker):
    """Check that the RequestConverter calculates the compatibility."""
    suite = PyTestTestSuite('foo')
    test_case = suite.create_and_add_test_case('bar')
    converter = RequestConverter(
        doc,
        Given(keyword='Und', text='der Auftrag 3 hat das Passwort 3.'),
        django_project,
        test_case,
    )
    mocker.patch('deep_translator.GoogleTranslator.translate', MockTranslator())
    assert converter.get_document_compatibility() >= min_compatibility
    assert converter.get_document_compatibility() <= max_compatibility
