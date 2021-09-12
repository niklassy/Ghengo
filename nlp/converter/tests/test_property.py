import pytest
from django.contrib.auth.models import User

from core.constants import Languages
from django_meta.api import Methods
from django_meta.model import ModelWrapper
from django_meta.project import DjangoProject
from django_sample_project.apps.order.models import Order
from nlp.converter.property import NewModelProperty, NewModelVariableProperty, MethodProperty, \
    ReferenceModelVariableProperty, ReferenceModelProperty, UserReferenceVariableProperty, \
    ModelCountProperty
from nlp.generate.pytest import PyTestModelFactoryExpression
from nlp.generate.pytest.suite import PyTestTestSuite
from nlp.generate.statement import AssignmentStatement
from nlp.generate.variable import Variable, VariableReference
from nlp.setup import Nlp
from nlp.tests.utils import MockTranslator
from nlp.utils import get_noun_chunks, NoToken

nlp = Nlp.for_language(Languages.DE)


class ConverterMock:
    def __init__(self, document):
        self.document = document
        self.language = document.lang_
        self.django_project = DjangoProject('django_sample_project.apps.config.settings')

    def get_noun_chunks(self):
        return get_noun_chunks(self.document)


def test_new_model_converter_property(mocker):
    """Check that when creating a new model with the property, that the value, chunk and token are set correctly."""
    mocker.patch('deep_translator.GoogleTranslator.translate', MockTranslator())
    doc = nlp('Gegeben sei ein Auftrag mit dem Namen "Mein Auftrag".')
    prop = NewModelProperty(ConverterMock(doc))
    assert doc[3] in prop.chunk
    assert isinstance(prop.value, ModelWrapper)
    assert prop.value.model == Order
    assert prop.token == doc[3]


@pytest.mark.parametrize(
    'doc, token_index', [
        (nlp('Gegeben sei ein Auftrag 1 mit dem Namen "Mein Auftrag".'), 4),
        (nlp('Gegeben sei ein Auftrag Order1 mit dem Namen "Mein Auftrag".'), 4),
        (nlp('Gegeben sei ein Auftrag "Mein Auftrag" mit dem Namen "Mein Auftrag".'), 4),
        (nlp('Gegeben sei ein Auftrag mit dem Namen "Mein Auftrag".'), None),
    ]
)
def test_new_variable_converter_property(mocker, doc, token_index):
    """Check that when creating a new variable with the property, that the value, chunk and token are set correctly."""
    mocker.patch('deep_translator.GoogleTranslator.translate', MockTranslator())
    converter = ConverterMock(doc)
    suite = PyTestTestSuite('foo')
    converter.test_case = suite.create_and_add_test_case('bar')
    converter.model = NewModelProperty(converter)
    prop = NewModelVariableProperty(converter)
    if token_index is not None:
        assert isinstance(prop.value, Variable)
        assert prop.value.reference_string == converter.model.value.name
        assert prop.token == doc[token_index]
    else:
        assert isinstance(prop.token, NoToken)


@pytest.mark.parametrize(
    'doc, token_index', [
        (nlp('Wenn der Benutzer Alice gelöscht wird'), 3),
        (nlp('Und der Benutzer Alice erhält das Passwort "Haus123"'), 3),
        (nlp('Und Alice erhält das Passwort "Haus123"'), 1),
        (nlp('Gegeben sei ein Auftrag 1'), None),
        (nlp('Wir sollten bald ankommen'), None),
    ]
)
def test_reference_variable_converter_property(doc, token_index, mocker):
    """Check that the property for referencing an earlier model works as expected."""
    mocker.patch('deep_translator.GoogleTranslator.translate', MockTranslator())
    converter = ConverterMock(doc)
    suite = PyTestTestSuite('foo')
    test_case = suite.create_and_add_test_case('bar')
    test_case.add_statement(AssignmentStatement(
        expression=PyTestModelFactoryExpression(ModelWrapper(User, None), []),
        variable=Variable('Alice', 'SOME_RANDOM_VALUE'),
    ))
    variable = Variable('Alice', 'User')
    test_case.add_statement(AssignmentStatement(
        expression=PyTestModelFactoryExpression(ModelWrapper(User, None), []),
        variable=variable,
    ))
    converter.test_case = test_case
    converter.model = NewModelProperty(converter)
    prop = ReferenceModelVariableProperty(converter)

    if token_index is None:
        assert isinstance(prop.token, NoToken)
        assert prop.value is None
    else:
        assert prop.token == doc[token_index]
        assert prop.value == variable


@pytest.mark.parametrize(
    'doc, token_index', [
        (nlp('Wenn Alice gelöscht wird'), 1),
        (nlp('Wenn der Auftrag Alice gelöscht wird'), 2),
        (nlp('Wenn Alice geändert wird'), 1),
    ]
)
def test_reference_model_converter_property(doc, token_index, mocker):
    """Referencing earlier models works via the property."""
    mocker.patch('deep_translator.GoogleTranslator.translate', MockTranslator())
    converter = ConverterMock(doc)
    suite = PyTestTestSuite('foo')
    test_case = suite.create_and_add_test_case('bar')
    variable = Variable('Alice', 'Order')
    test_case.add_statement(AssignmentStatement(
        expression=PyTestModelFactoryExpression(ModelWrapper(Order, None), []),
        variable=variable,
    ))
    converter.test_case = test_case
    converter.model = NewModelProperty(converter)
    converter.variable_ref = ReferenceModelVariableProperty(converter)
    converter.variable_ref.calculate_value()
    prop = ReferenceModelProperty(converter)

    assert isinstance(prop.value, ModelWrapper)
    assert prop.value.model == Order
    assert prop.token == doc[token_index]


@pytest.mark.parametrize(
    'doc, token_index', [
        (nlp('Wenn Alice einen Auftrag löscht'), 1),
        (nlp('Wenn ein Auftrag erstellt wird'), None),
        (nlp('Wenn Alice an einen Auftrag teilnimmt'), 1),
        (nlp('Wenn Bob an einen Auftrag teilnimmt'), None),
    ]
)
def test_reference_user_converter_property(doc, token_index, mocker):
    """Referencing earlier users works via the property."""
    mocker.patch('deep_translator.GoogleTranslator.translate', MockTranslator())
    converter = ConverterMock(doc)
    suite = PyTestTestSuite('foo')
    test_case = suite.create_and_add_test_case('bar')
    variable = Variable('Alice', 'User')
    test_case.add_statement(AssignmentStatement(
        expression=PyTestModelFactoryExpression(ModelWrapper(User, None), []),
        variable=variable,
    ))
    converter.test_case = test_case
    converter.model = NewModelProperty(converter)
    converter.variable = ReferenceModelVariableProperty(converter)
    converter.variable.calculate_value()
    prop = UserReferenceVariableProperty(converter)

    if token_index is None:
        assert prop.value is None
        assert isinstance(prop.token, NoToken)
    else:
        assert isinstance(prop.value, VariableReference)
        assert prop.value.reference_string == 'User'
        assert prop.token == doc[token_index]


@pytest.mark.parametrize(
    'doc, token_index, expected_method', [
        (nlp('Wenn ein Auftrag erstellt wird'), 3, Methods.POST),
        (nlp('Wenn die Liste der Aufträge geholt wird'), 2, Methods.GET),
        (nlp('Wenn die Details des Auftrags 1 geholt werden'), 2, Methods.GET),
        (nlp('Wenn Benutzer 2 gelöscht wird'), 3, Methods.DELETE),
        (nlp('Wenn der Benutzer Alice gelöscht wird'), 4, Methods.DELETE),
        (nlp('Wenn das ToDo aktualisiert wird'), 3, Methods.PUT),
        (nlp('Wenn das ToDo geändert wird'), 3, Methods.PUT),
    ]
)
def test_method_converter_property(mocker, doc, token_index, expected_method):
    """Check that when searching for a method with the property, that the value, chunk and token are set correctly."""
    mocker.patch('deep_translator.GoogleTranslator.translate', MockTranslator())
    converter = ConverterMock(doc)
    prop = MethodProperty(converter)
    assert prop.chunk is None
    assert prop.value == expected_method
    assert prop.token == doc[token_index]


@pytest.mark.parametrize(
    'doc, token_index, expected_value', [
        (nlp('Dann sollte es 2 Aufträge geben'), 3, '2'),
        (nlp('Dann sollte es zwei Aufträge geben'), 3, 'zwei'),
        (nlp('Dann gibt es sieben oder mehr Aufträge'), 3, 'sieben'),
    ]
)
def test_model_count_property(mocker, doc, token_index, expected_value):
    mocker.patch('deep_translator.GoogleTranslator.translate', MockTranslator())
    converter = ConverterMock(doc)
    prop = ModelCountProperty(converter)
    converter.model = NewModelProperty(converter)
    assert prop.chunk == converter.model.chunk
    assert prop.value == expected_value
    assert prop.token == doc[token_index]
