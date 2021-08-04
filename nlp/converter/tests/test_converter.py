import pytest
from django.contrib.auth.models import User

from core.constants import Languages
from django_meta.model import ModelAdapter
from django_meta.project import DjangoProject
from django_sample_project.apps.order.models import Order
from gherkin.ast import Given, DataTable, TableRow, TableCell, Then
from nlp.converter.converter import ModelFactoryConverter, ModelVariableReferenceConverter, RequestConverter, \
    QuerysetConverter, CountQuerysetConverter, ExistsQuerysetConverter, ManyCheckEntryResponseConverter, \
    ResponseConverterBase, ManyLengthResponseConverter, ManyResponseConverter, ResponseConverter, \
    ResponseErrorConverter, ResponseStatusCodeConverter, ObjectQuerysetConverter, AssertPreviousModelConverter
from nlp.generate.argument import Kwarg
from nlp.generate.constants import CompareChar
from nlp.generate.expression import ModelSaveExpression, APIClientExpression, RequestExpression, \
    APIClientAuthenticateExpression, ModelQuerysetFilterExpression, ModelQuerysetAllExpression, CompareExpression, \
    ModelQuerysetGetExpression
from nlp.generate.pytest import PyTestModelFactoryExpression
from nlp.generate.pytest.suite import PyTestTestSuite
from nlp.generate.statement import AssignmentStatement, ModelFieldAssignmentStatement
from nlp.generate.variable import Variable
from nlp.generate.warning import GenerationWarning
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


def test_model_variable_reference_converter(mocker):
    """Check that the ModelVariableReferenceConverter correctly creates statements to modify an object."""
    mocker.patch('deep_translator.GoogleTranslator.translate', MockTranslator())
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
    mocker.patch('deep_translator.GoogleTranslator.translate', MockTranslator())
    given = Given(keyword='Und', text='Alice erhält das Passwort "Haus123"')
    suite = PyTestTestSuite('foo')
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
    mocker.patch('deep_translator.GoogleTranslator.translate', MockTranslator())
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
    assert converter.get_document_compatibility() >= min_compatibility
    assert converter.get_document_compatibility() <= max_compatibility


def test_model_request_converter(mocker):
    """Check that the RequestConverter correctly creates statements to send requests."""
    mocker.patch('deep_translator.GoogleTranslator.translate', MockTranslator())
    given = Given(keyword='Wenn', text='Alice einen Auftrag holt')
    suite = PyTestTestSuite('foo')
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
    mocker.patch('deep_translator.GoogleTranslator.translate', MockTranslator())
    given = Given(keyword='Wenn', text='Alice einen Auftrag holt')
    suite = PyTestTestSuite('foo')
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
    mocker.patch('deep_translator.GoogleTranslator.translate', MockTranslator())
    given = Given(keyword='Wenn', text='Alice einen Auftrag holt')
    suite = PyTestTestSuite('foo')
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
        (nlp('Wenn ein Auftrag gelöscht wird'), 0.7, 1),
        (nlp('Wenn Alice einen Auftrag erstellt'), 0.7, 1),
        (nlp('Gegeben sei ein Auftrag'), 0, 0.1),
        (nlp('Und ein Benutzer Alice'), 0, 0.1),
        (nlp('Sie fahren mit dem Auto'), 0, 0.1),
    ]
)
def test_model_request_converter_compatibility(doc, min_compatibility, max_compatibility, mocker):
    """Check that the RequestConverter calculates the compatibility."""
    mocker.patch('deep_translator.GoogleTranslator.translate', MockTranslator())
    suite = PyTestTestSuite('foo')
    test_case = suite.create_and_add_test_case('bar')
    test_case.add_statement(AssignmentStatement(
        expression=PyTestModelFactoryExpression(ModelAdapter(User, None), []),
        variable=Variable('Alice', 'User'),
    ))
    converter = RequestConverter(
        doc,
        Given(keyword='Und', text='der Auftrag 3 hat das Passwort 3.'),
        django_project,
        test_case,
    )
    assert converter.get_document_compatibility() >= min_compatibility
    assert converter.get_document_compatibility() <= max_compatibility


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


def add_request_statement(test_case, doc=None):
    """
    Creates and adds a request statement to a test case.
    """
    if doc is None:
        doc = nlp('Wenn ein Auftrag erstellt wird')

    converter = RequestConverter(
        doc,
        Given(keyword='Und', text='der Auftrag 3 hat das Passwort 3.'),
        django_project,
        test_case,
    )

    for statement in converter.convert_to_statements():
        test_case.add_statement(statement)


@pytest.mark.parametrize(
    'doc, min_compatibility, max_compatibility, with_request', [
        (nlp('Dann sollte die Antwort stimmen.'), 0, 0.2, False),
        (nlp('Dann sollte die Antwort stimmen.'), 0.7, 1, True),
        (nlp('Ich rede komisches Zeug.'), 0.7, 1, True),
        (nlp('Ich rede komisches Zeug.'), 0, 0.2, False),
    ]
)
def test_response_base_converter_compatibility(doc, min_compatibility, max_compatibility, mocker, with_request):
    """Check that the ResponseConverterBase detects the compatibility of different documents correctly."""
    mocker.patch('deep_translator.GoogleTranslator.translate', MockTranslator())
    suite = PyTestTestSuite('foo')
    test_case = suite.create_and_add_test_case('bar')

    if with_request:
        add_request_statement(test_case)
        assert len(test_case.statements) > 0

    converter = ResponseConverterBase(
        doc,
        Given(keyword='Gegeben sei', text='ein Auftrag mit der Nummer 3'),
        django_project,
        test_case,
    )
    assert converter.get_document_compatibility() >= min_compatibility
    assert converter.get_document_compatibility() <= max_compatibility


@pytest.mark.parametrize(
    'doc, request_doc, expected_value', [
        (nlp('Dann sollte der Auftrag den Namen Alice haben.'), nlp('Wenn ein Auftrag erstellt wird.'), True),
        (nlp('Dann sollte das ToDo den Namen Alice haben.'), nlp('Wenn ein Auftrag erstellt wird.'), False),
        (nlp('Dann sollte das ToDo den Namen Alice haben.'), nlp('Wenn ein ToDo erstellt wird.'), True),
    ]
)
def test_response_base_converter_model_in_text(mocker, doc, expected_value, request_doc):
    """Check that the converter correctly detects if the model in the text fits the request."""
    mocker.patch('deep_translator.GoogleTranslator.translate', MockTranslator())
    suite = PyTestTestSuite('foo')
    test_case = suite.create_and_add_test_case('bar')
    add_request_statement(test_case, request_doc)

    converter = ResponseConverterBase(
        doc,
        Given(keyword='Gegeben sei', text='ein Auftrag mit der Nummer 3'),
        django_project,
        test_case,
    )
    assert converter.model_in_text_fits_request == expected_value


@pytest.mark.parametrize(
    'doc, min_compatibility, max_compatibility', [
        (nlp('Dann sollte der zweite Eintrag den Namen "Alice" haben.'), 0.7, 1),
        (nlp('Dann sollte der zweite Auftrag den Namen "Alice" haben.'), 0.7, 1),
        (nlp('Dann sollte die Antwort zwei Einträge haben.'), 0, 0.4),
        (nlp('Dann sollte der Auftrag den Namen "Alice" haben.'), 0, 0.4),
        (nlp('Dann sollte die Antwort den Status 200 haben.'), 0, 0.4),
        (nlp('Dann sollte der Fehler "abc" enthalten.'), 0, 0.4),
    ]
)
def test_many_check_entry_response_converter_compatibility(doc, min_compatibility, max_compatibility, mocker):
    """Check that the ManyCheckEntryResponseConverter detects the compatibility of different documents correctly."""
    mocker.patch('deep_translator.GoogleTranslator.translate', MockTranslator())
    suite = PyTestTestSuite('foo')
    test_case = suite.create_and_add_test_case('bar')

    add_request_statement(test_case)
    assert len(test_case.statements) > 0

    converter = ManyCheckEntryResponseConverter(
        doc,
        Given(keyword='Gegeben sei', text='ein Auftrag mit der Nummer 3'),
        django_project,
        test_case,
    )
    assert converter.get_document_compatibility() >= min_compatibility
    assert converter.get_document_compatibility() <= max_compatibility


@pytest.mark.parametrize(
    'doc, desired_entry_index, field_count', [
        (nlp('Dann sollte der zweite Eintrag den Namen "Alice" haben.'), 1, 1),
        (nlp('Dann sollte der zweite Auftrag den Namen "Alice" haben.'), 1, 1),
        (nlp('Dann sollte der zweite Auftrag den Namen "Alice" und die Beschreibung "Test" haben.'), 1, 2),
        (nlp('Dann sollte der dritte Auftrag den Namen "Alice" haben.'), 2, 1),
        (nlp('Dann sollte der dritte Eintrag den Namen "Alice" haben.'), 2, 1),
        (nlp('Dann sollte der fünfte Auftrag den Namen "Alice" haben.'), 4, 1),
        (nlp('Dann sollte der fünfte Eintrag den Namen "Alice" haben.'), 4, 1),
        (nlp('Dann sollte der Auftrag den Namen "Alice" haben.'), None, 1),
        (nlp('Dann sollte der Eintrag den Namen "Alice" haben.'), None, 1),
    ]
)
def test_many_check_entry_response_converter_output(doc, desired_entry_index, mocker, field_count):
    """Check that the ManyCheckEntryResponseConverter detects the compatibility of different documents correctly."""
    mocker.patch('deep_translator.GoogleTranslator.translate', MockTranslator())
    suite = PyTestTestSuite('foo')
    test_case = suite.create_and_add_test_case('bar')

    add_request_statement(test_case)

    converter = ManyCheckEntryResponseConverter(
        doc,
        Given(keyword='Gegeben sei', text='ein Auftrag mit der Nummer 3'),
        django_project,
        test_case,
    )
    statements = converter.convert_to_statements()
    assert len(statements) == field_count + 1
    if desired_entry_index:
        assert statements[0].expression.child.index == desired_entry_index
    else:
        assert isinstance(statements[0].expression.child.index, GenerationWarning)

    # check that the correct amount of fields is returned in statements after the first one
    assert len(statements[1:]) == field_count


@pytest.mark.parametrize(
    'doc, min_compatibility, max_compatibility', [
        (nlp('Dann sollte der zweite Eintrag den Namen "Alice" haben.'), 0, 0.3),
        (nlp('Dann sollte der zweite Auftrag den Namen "Alice" haben.'), 0, 0.3),
        (nlp('Dann sollte die Antwort zwei Einträge haben.'), 0.7, 1),
        (nlp('Dann sollte die Antwort vier Aufträge haben.'), 0.7, 1),
        (nlp('Dann sollte vier Einträge enthalten sein.'), 0.7, 1),
        (nlp('Dann sollte der Auftrag den Namen "Alice" haben.'), 0, 0.4),
        (nlp('Dann sollte die Antwort den Status 200 haben.'), 0, 0.4),
        (nlp('Dann sollte der Fehler "abc" enthalten.'), 0, 0.4),
    ]
)
def test_many_check_length_response_converter_compatibility(doc, min_compatibility, max_compatibility, mocker):
    """Check that the ManyLengthResponseConverter detects the compatibility of different documents correctly."""
    mocker.patch('deep_translator.GoogleTranslator.translate', MockTranslator())
    suite = PyTestTestSuite('foo')
    test_case = suite.create_and_add_test_case('bar')

    add_request_statement(test_case)
    assert len(test_case.statements) > 0

    converter = ManyLengthResponseConverter(
        doc,
        Given(keyword='Gegeben sei', text='ein Auftrag mit der Nummer 3'),
        django_project,
        test_case,
    )
    assert converter.get_document_compatibility() >= min_compatibility
    assert converter.get_document_compatibility() <= max_compatibility


@pytest.mark.parametrize(
    'doc, desired_length', [
        (nlp('Dann sollte die Antwort einen Eintrag haben.'), 1),
        (nlp('Dann sollte die Antwort sieben Einträge haben.'), 7),
        (nlp('Dann sollte die Antwort sieben Einträge haben.'), 7),
        (nlp('Dann sollten drei Aufträge gegeben sein.'), 3),
        (nlp('Dann sollten drei Aufträge zurückgegeben werden.'), 3),
        (nlp('Dann sollte ein Auftrag gegeben sein.'), 1),
    ]
)
def test_many_check_length_response_converter_output(doc, desired_length, mocker):
    """Check that the output of ManyLengthResponseConverter is correct."""
    mocker.patch('deep_translator.GoogleTranslator.translate', MockTranslator())
    suite = PyTestTestSuite('foo')
    test_case = suite.create_and_add_test_case('bar')

    add_request_statement(test_case)

    converter = ManyLengthResponseConverter(
        doc,
        Given(keyword='Gegeben sei', text='ein Auftrag mit der Nummer 3'),
        django_project,
        test_case,
    )
    statements = converter.convert_to_statements()
    assert len(statements) == 1
    assert statements[0].expression.value_2.value == desired_length
    assert statements[0].expression.value_1.function_name == 'len'
    assert statements[0].expression.value_1.function_kwargs[0].variable == converter.get_referenced_response_variable()
    assert statements[0].expression.value_1.function_kwargs[0].attribute_name == 'data'


@pytest.mark.parametrize(
    'doc, min_compatibility, max_compatibility', [
        (nlp('Dann sollte der zweite Eintrag den Namen "Alice" haben.'), 0.7, 1),
        (nlp('Dann sollte der zweite Auftrag der Liste den Namen "Alice" haben.'), 0.7, 1),
        (nlp('Dann sollte der zweite Eintrag der Liste den Namen "Alice" haben.'), 0.7, 1),
        (nlp('Dann sollte die Antwort eine Länge von 2 haben.'), 0.7, 1),
        (nlp('Dann sollte die Antwort zwei Einträge haben.'), 0.7, 1),
        (nlp('Dann sollten fünf Einträge enthalten sein.'), 0.7, 1),
        (nlp('Dann sollten in der ersten Antwort zwei Einträge enthalten sein.'), 0.7, 1),
        (nlp('Dann sollte der erste Eintrag in der Antwort den Namen "Alice" enthalten.'), 0.7, 1),
        (nlp('Dann sollte der erste Auftrag in der Antwort den Namen "Alice" enthalten.'), 0.7, 1),
        (nlp('Dann sollte die Antwort den Namen "Alice" enthalten.'), 0, 0.3),
    ]
)
def test_many_response_converter_compatibility(doc, min_compatibility, max_compatibility, mocker):
    """Check that the ManyResponseConverter detects the compatibility of different documents correctly."""
    mocker.patch('deep_translator.GoogleTranslator.translate', MockTranslator())
    suite = PyTestTestSuite('foo')
    test_case = suite.create_and_add_test_case('bar')

    add_request_statement(test_case)
    assert len(test_case.statements) > 0

    converter = ManyResponseConverter(
        doc,
        Given(keyword='Gegeben sei', text='ein Auftrag mit der Nummer 3'),
        django_project,
        test_case,
    )
    assert converter.get_document_compatibility() >= min_compatibility
    assert converter.get_document_compatibility() <= max_compatibility


@pytest.mark.parametrize(
    'doc, min_compatibility, max_compatibility', [
        (nlp('Dann sollte die Antwort den Namen "Alice" enthalten.'), 0.7, 1),
        (nlp('Dann sollte der Auftrag den Namen "Alice" enthalten.'), 0.7, 1),
        (nlp('Dann sollte in der Auftrag der Namen "Alice" sein.'), 0.7, 1),
        (nlp('Dann sollte der Benutzer den Namen "Alice" haben.'), 0, 0.5),
    ]
)
def test_response_converter_compatibility(doc, min_compatibility, max_compatibility, mocker):
    """Check that the ResponseConverter detects the compatibility of different documents correctly."""
    mocker.patch('deep_translator.GoogleTranslator.translate', MockTranslator())
    suite = PyTestTestSuite('foo')
    test_case = suite.create_and_add_test_case('bar')

    add_request_statement(test_case)
    assert len(test_case.statements) > 0

    converter = ResponseConverter(
        doc,
        Given(keyword='Gegeben sei', text='ein Auftrag mit der Nummer 3'),
        django_project,
        test_case,
    )
    assert converter.get_document_compatibility() >= min_compatibility
    assert converter.get_document_compatibility() <= max_compatibility


@pytest.mark.parametrize(
    'doc, field_names', [
        (nlp('Dann sollte die Antwort existieren'), []),
        (nlp('Dann sollte die Antwort den Namen "Alice" enthalten.'), ['name']),
        (nlp('Dann sollte die Antwort den Namen "Alice" und die Beschreibung "Test" enthalten.'), ['name', 'description']),
    ]
)
def test_response_converter_output(doc, mocker, field_names):
    """Check that the output of ResponseConverter is correct."""
    mocker.patch('deep_translator.GoogleTranslator.translate', MockTranslator())
    suite = PyTestTestSuite('foo')
    test_case = suite.create_and_add_test_case('bar')

    amount_of_checked_fields = len(field_names)
    add_request_statement(test_case)

    converter = ResponseConverter(
        doc,
        Given(keyword='Gegeben sei', text='ein Auftrag mit der Nummer 3'),
        django_project,
        test_case,
    )
    statements = converter.convert_to_statements()
    if amount_of_checked_fields > 0:
        assert len(statements) == 1 + amount_of_checked_fields
        # check the statement that sets the variable
        assert statements[0].expression.child.attribute_name == 'data'

        # check the statements that are assert statements for each field
        for index, statement in enumerate(statements[1:]):
            assert statement.expression.value_1.function_name.attribute_name == 'get'
            assert statement.expression.value_1.function_kwargs[0].value == field_names[index]
    else:
        assert len(statements) == 0


@pytest.mark.parametrize(
    'doc, min_compatibility, max_compatibility', [
        (nlp('Dann sollte die Antwort den Status 200 haben.'), 0.7, 1),
        (nlp('Dann sollte die Antwort den Status 400 haben.'), 0.7, 1),
        (nlp('Dann sollte die Antwort den Status 403 haben.'), 0.7, 1),
        (nlp('Dann sollte die Antwort den Namen Alice enthalten.'), 0, 0.3),
        (nlp('Dann sollte die Antwort die Beschreibung "test" enthalten.'), 0, 0.3),
        (nlp('Dann sollte der zweite Eintrag den Namen Alice enthalten.'), 0, 0.3),
        (nlp('Dann sollten sieben Eintrage zurückgegeben werden.'), 0, 0.3),
    ]
)
def test_many_response_converter_compatibility(doc, min_compatibility, max_compatibility, mocker):
    """Check that the ResponseStatusCodeConverter detects the compatibility of different documents correctly."""
    mocker.patch('deep_translator.GoogleTranslator.translate', MockTranslator())
    suite = PyTestTestSuite('foo')
    test_case = suite.create_and_add_test_case('bar')

    add_request_statement(test_case)
    assert len(test_case.statements) > 0

    converter = ResponseStatusCodeConverter(
        doc,
        Given(keyword='Gegeben sei', text='ein Auftrag mit der Nummer 3'),
        django_project,
        test_case,
    )
    assert converter.get_document_compatibility() >= min_compatibility
    assert converter.get_document_compatibility() <= max_compatibility


@pytest.mark.parametrize(
    'doc, status_code', [
        (nlp('Dann sollte die Antwort existieren'), None),
        (nlp('Dann sollte die Antwort den Status 200 haben.'), 200),
        (nlp('Dann sollte die Antwort den Status 400 haben.'), 400),
        (nlp('Dann sollte die Antwort den Status 404 haben.'), 404),
    ]
)
def test_response_converter_output(doc, mocker, status_code):
    """Check that the output of ResponseStatusCodeConverter is correct."""
    mocker.patch('deep_translator.GoogleTranslator.translate', MockTranslator())
    suite = PyTestTestSuite('foo')
    test_case = suite.create_and_add_test_case('bar')

    add_request_statement(test_case)

    converter = ResponseStatusCodeConverter(
        doc,
        Given(keyword='Gegeben sei', text='ein Auftrag mit der Nummer 3'),
        django_project,
        test_case,
    )
    statements = converter.convert_to_statements()
    if status_code:
        assert len(statements) == 1
        assert statements[0].expression.value_1.attribute_name == 'status_code'
        assert statements[0].expression.value_2.value == status_code
    else:
        assert len(statements) == 0


@pytest.mark.parametrize(
    'doc, min_compatibility, max_compatibility', [
        (nlp('Dann sollte der Fehler "asd" enthalten.'), 0.7, 1),
        (nlp('Dann sollte es einen Fehler "error" geben.'), 0.7, 1),
        (nlp('Dann sollte ein Auftrag existieren.'), 0, 0.3),
        (nlp('Dann sollte ein Test existieren.'), 0, 0.3),
        (nlp('Dann sollte die Antwort zwei Einträge enthalten.'), 0, 0.3),
    ]
)
def test_many_response_converter_compatibility(doc, min_compatibility, max_compatibility, mocker):
    """Check that the ResponseErrorConverter detects the compatibility of different documents correctly."""
    mocker.patch('deep_translator.GoogleTranslator.translate', MockTranslator())
    suite = PyTestTestSuite('foo')
    test_case = suite.create_and_add_test_case('bar')

    add_request_statement(test_case)
    assert len(test_case.statements) > 0

    converter = ResponseErrorConverter(
        doc,
        Given(keyword='Gegeben sei', text='ein Auftrag mit der Nummer 3'),
        django_project,
        test_case,
    )
    assert converter.get_document_compatibility() >= min_compatibility
    assert converter.get_document_compatibility() <= max_compatibility


@pytest.mark.parametrize(
    'doc, error_str', [
        (nlp('Dann sollte die Antwort existieren'), None),
        (nlp('Dann sollte die Antwort den Fehler "asd" haben.'), 'asd'),
        (nlp('Dann sollte die Antwort einen Fehler "error" zurückgeben.'), 'error'),
    ]
)
def test_response_converter_output(doc, mocker, error_str):
    """Check that the output of ResponseErrorConverter is correct."""
    mocker.patch('deep_translator.GoogleTranslator.translate', MockTranslator())
    suite = PyTestTestSuite('foo')
    test_case = suite.create_and_add_test_case('bar')

    add_request_statement(test_case)

    converter = ResponseErrorConverter(
        doc,
        Given(keyword='Gegeben sei', text='ein Auftrag mit der Nummer 3'),
        django_project,
        test_case,
    )
    statements = converter.convert_to_statements()
    if error_str:
        assert len(statements) == 1
        assert statements[0].expression.value_1.value == error_str
        assert statements[0].expression.compare_char == 'in'
        assert statements[0].expression.value_2.function_name == 'str'
        assert statements[0].expression.value_2.function_kwargs[0].attribute_name == 'data'
    else:
        assert len(statements) == 0


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
        expression=PyTestModelFactoryExpression(ModelAdapter(User, None), [Kwarg('bar', 123)]),
        variable=Variable('Alice', 'User'),     # <- variable name is Alice
    ))
    test_case.add_statement(AssignmentStatement(
        expression=PyTestModelFactoryExpression(ModelAdapter(Order, None), [Kwarg('bar', 123)]),
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
        (nlp('Dann sollte der Auftrag 1 den Namen "Alice" haben.'), ['name'], 'order'),
        (nlp('Dann sollte der Auftrag 1 den Namen "Alice" und den Wert "Test" haben.'), ['name', 'worth'], 'order'),
    ]
)
def test_object_qs_converter_output(doc, mocker, filter_fields, variable_type):
    """Check that the output of AssertPreviousModelConverter is correct."""
    assert variable_type in ['order', 'user', None]

    mocker.patch('deep_translator.GoogleTranslator.translate', MockTranslator())
    suite = PyTestTestSuite('foo')
    test_case = suite.create_and_add_test_case('bar')

    # add two statements: a user `alice` and an `order_1`
    user_variable = Variable('Alice', 'User')
    order_variable = Variable('1', 'Order')

    if variable_type == 'user':
        referenced_variable = user_variable
    elif variable_type == 'order':
        referenced_variable = order_variable
    else:
        referenced_variable = None

    test_case.add_statement(AssignmentStatement(
        expression=PyTestModelFactoryExpression(ModelAdapter(User, None), [Kwarg('bar', 123)]),
        variable=user_variable,
    ))
    test_case.add_statement(AssignmentStatement(
        expression=PyTestModelFactoryExpression(ModelAdapter(Order, None), [Kwarg('bar', 123)]),
        variable=order_variable,
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
            assert exp.value_1.variable == referenced_variable

