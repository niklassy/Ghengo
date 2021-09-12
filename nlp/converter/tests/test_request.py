import pytest
from django.contrib.auth.models import User

from core.constants import Languages
from django_meta.api import Methods
from django_meta.model import ModelWrapper
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
        expression=PyTestModelFactoryExpression(ModelWrapper(User, None), [Kwarg('bar', 123)]),
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
        expression=PyTestModelFactoryExpression(ModelWrapper(User, None), [Kwarg('bar', 123)]),
        variable=Variable('Alice', 'User'),  # <-- variable defined
    ))
    converter = RequestConverter(nlp('Wenn ein Auftrag erstellt wird'), given, django_project, test_case)
    statements = converter.convert_to_statements()
    assert len(statements) == 2     # client  + request
    assert converter.from_anonymous_user is True
    assert isinstance(statements[0].expression, APIClientExpression)
    assert isinstance(statements[1].expression, RequestExpression)


@pytest.mark.parametrize(
    'doc, method, reverse_name', [
        (nlp('Wenn Alice den Auftrag 1 löscht'), Methods.DELETE, 'orders-detail'),
        (nlp('Wenn die Liste der Aufträge geholt wird'), Methods.GET, 'orders-list'),
        (nlp('Wenn die Details des Auftrag 1 geholt wird'), Methods.GET, 'orders-detail'),
        (nlp('Wenn ein Auftrag mit dem Namen "Test" erstellt wird.'), Methods.POST, 'orders-detail'),
        (nlp('Wenn der Auftrag 1 so geändert wird, dass der Name "foo" ist'), Methods.PUT, 'orders-detail'),
        (nlp('Wenn der Auftrag 1 gebucht wird'), Methods.POST, 'orders-book'),
    ]
)
def test_model_request_converter_reverse_name(doc, method, reverse_name, mocker):
    """Check that the correct reverse is given."""
    mocker.patch('deep_translator.GoogleTranslator.translate', MockTranslator())
    given = Given(keyword='Wenn', text='Alice einen Auftrag holt')
    suite = PyTestTestSuite('foo')
    test_case = suite.create_and_add_test_case('bar')
    test_case.add_statement(AssignmentStatement(
        expression=PyTestModelFactoryExpression(ModelWrapper(User, None), []),
        variable=Variable('Alice', 'User'),
    ))
    order_variable = Variable('1', 'Order')
    test_case.add_statement(AssignmentStatement(
        expression=PyTestModelFactoryExpression(ModelWrapper(Order, None), []),
        variable=order_variable,
    ))
    converter = RequestConverter(doc, given, django_project, test_case)
    statements = converter.convert_to_statements()
    api_call_expression = statements[-1].expression
    reverse_expression = statements[-1].expression.reverse_expression
    assert reverse_expression.reverse_name.value == reverse_name
    assert api_call_expression.function_name == method


@pytest.mark.parametrize(
    'doc, variable_string, model_token_index, model_variable_index, user_var_index, data_field_names', [
        (nlp('Wenn Alice den Auftrag 1 löscht'), 'Alice', 3, 4, 1, ['pk']),
        (nlp('Wenn der Benutzer 1 den Auftrag 1 löscht'), '1', 5, 6, 3, ['pk']),
        (nlp('Wenn der Benutzer 1 die Liste der Aufträge, die abgeschlossen sind, holt.'), '1', 7, None, 3, ['closed']),
        (nlp('Wenn der Benutzer 1 die Liste der abgeschlossenen Aufträge holt.'), '1', 8, None, 3, ['closed']),
        (nlp('Wenn der Benutzer 1 den Auftrag 1 so ändert, dass der Name "foo" ist.'), '1', 5, 6, 3, ['name', 'pk']),
    ]
)
def test_model_request_converter_with_reference(
    mocker,
    doc,
    variable_string,
    model_token_index,
    model_variable_index,
    user_var_index,
    data_field_names,
):
    """Check that a converter with a reference to a model sets all properties correctly and has the correct output."""
    mocker.patch('deep_translator.GoogleTranslator.translate', MockTranslator())
    given = Given(keyword='Wenn', text='Alice einen Auftrag holt')
    suite = PyTestTestSuite('foo')
    test_case = suite.create_and_add_test_case('bar')
    test_case.add_statement(AssignmentStatement(
        expression=PyTestModelFactoryExpression(ModelWrapper(User, None), []),
        variable=Variable(variable_string, 'User'),
    ))
    order_variable = Variable('1', 'Order')
    test_case.add_statement(AssignmentStatement(
        expression=PyTestModelFactoryExpression(ModelWrapper(Order, None), []),
        variable=order_variable,
    ))
    converter = RequestConverter(doc, given, django_project, test_case)
    statements = converter.convert_to_statements()

    # check all the properties
    assert isinstance(converter.model.value, ModelWrapper)
    assert converter.model.value.model == Order
    assert converter.model.token == doc[model_token_index]
    if model_variable_index is not None:
        assert converter.model_variable_ref.value == order_variable
        assert converter.model_variable_ref.token == doc[model_variable_index]
    else:
        assert not converter.model_variable_ref.token
    assert converter.user.token == doc[user_var_index]

    assert len(statements) == 3
    assert isinstance(statements[0].expression, APIClientExpression)
    assert isinstance(statements[1].expression, APIClientAuthenticateExpression)
    assert isinstance(statements[2].expression, RequestExpression)
    # check that the reverse expression holds the data of the order variable
    reverse_kwargs = statements[2].expression.reverse_expression.function_kwargs
    request_kwargs = statements[2].expression.function_kwargs
    assert len(reverse_kwargs) + len(request_kwargs) == len(data_field_names)

    for i, field_name in enumerate(data_field_names):
        # if a primary key was meant, check that there is a variable
        if field_name == 'pk':
            attribute = reverse_kwargs[0].value.value
            assert attribute.variable_ref == order_variable
        else:
            # check that the field name is correct
            assert converter.extractors[i].field_name == field_name


@pytest.mark.parametrize(
    'doc, min_compatibility, max_compatibility', [
        (nlp('Wenn ein Auftrag erstellt wird'), 0.7, 1),
        (nlp('Wenn ein Auftrag mit dem Namen "Test" und der Nummer 3 erstellt wird'), 0.7, 1),
        (nlp('Wenn ein Auftrag geändert wird'), 0.7, 1),
        (nlp('Wenn ein Auftrag aktualisiert wird'), 0.7, 1),
        (nlp('Wenn die Liste der Aufträge geholt wird'), 0.7, 1),
        (nlp('Wenn ein Auftrag gelöscht wird'), 0.7, 1),
        (nlp('Wenn Alice einen Auftrag erstellt'), 0.7, 1),
    ]
)
def test_model_request_converter_compatibility(doc, min_compatibility, max_compatibility, mocker):
    """Check that the RequestConverter calculates the compatibility."""
    mocker.patch('deep_translator.GoogleTranslator.translate', MockTranslator())
    suite = PyTestTestSuite('foo')
    test_case = suite.create_and_add_test_case('bar')
    test_case.add_statement(AssignmentStatement(
        expression=PyTestModelFactoryExpression(ModelWrapper(User, None), []),
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
