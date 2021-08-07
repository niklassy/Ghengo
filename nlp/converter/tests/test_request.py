import pytest
from django.contrib.auth.models import User

from core.constants import Languages
from django_meta.model import ModelAdapter
from django_meta.project import DjangoProject
from django_sample_project.apps.order.models import Order
from gherkin.ast import Given
from nlp.converter.request import RequestConverter
from nlp.generate.argument import Kwarg
from nlp.generate.expression import APIClientExpression, RequestExpression, APIClientAuthenticateExpression
from nlp.generate.pytest import PyTestModelFactoryExpression
from nlp.generate.pytest.suite import PyTestTestSuite
from nlp.generate.statement import AssignmentStatement
from nlp.generate.variable import Variable
from nlp.setup import Nlp
from nlp.tests.utils import MockTranslator

nlp = Nlp.for_language(Languages.DE)
default_doc = nlp('Wenn Alice eine Anfrage macht')
django_project = DjangoProject('django_sample_project.apps.config.settings')


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


@pytest.mark.parametrize(
    'doc, variable_string, model_token_index, model_variable_index, user_var_index', [
        (nlp('Wenn Alice den Auftrag 1 löscht'), 'Alice', 3, 4, 1),
        (nlp('Wenn der Benutzer 1 den Auftrag 1 löscht'), '1', 5, 6, 3),
    ]
)
def test_model_request_converter_with_reference(
    mocker,
    doc,
    variable_string,
    model_token_index,
    model_variable_index,
    user_var_index,
):
    """Check that a converter with a reference to a model sets all properties correctly and has the correct output."""
    mocker.patch('deep_translator.GoogleTranslator.translate', MockTranslator())
    given = Given(keyword='Wenn', text='Alice einen Auftrag holt')
    suite = PyTestTestSuite('foo')
    test_case = suite.create_and_add_test_case('bar')
    test_case.add_statement(AssignmentStatement(
        expression=PyTestModelFactoryExpression(ModelAdapter(User, None), []),
        variable=Variable(variable_string, 'User'),
    ))
    order_variable = Variable('1', 'Order')
    test_case.add_statement(AssignmentStatement(
        expression=PyTestModelFactoryExpression(ModelAdapter(Order, None), []),
        variable=order_variable,
    ))
    converter = RequestConverter(doc, given, django_project, test_case)
    statements = converter.convert_to_statements()

    # check all the properties
    assert isinstance(converter.model.value, ModelAdapter)
    assert converter.model.value.model == Order
    assert converter.model.token == doc[model_token_index]
    assert converter.model_variable.value == order_variable
    assert converter.model_variable.token == doc[model_variable_index]
    assert converter.user.token == doc[user_var_index]

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
