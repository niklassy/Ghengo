import pytest
from django.db.models import CharField
from rest_framework import serializers

from core.constants import Languages
from django_meta.api import AbstractApiFieldAdapter, ApiFieldAdapter
from django_meta.model import ModelAdapter
from django_sample_project.apps.order.models import ToDo
from nlp.extractor.exception import ExtractionError
from nlp.extractor.fields_rest_api import ApiModelFieldExtractor, BooleanApiModelFieldExtractor, \
    IntegerApiModelFieldExtractor, FloatApiModelFieldExtractor, NoneApiModelFieldExtractor, \
    StringApiModelFieldExtractor, ModelApiFieldExtractor, ForeignKeyApiFieldExtractor, DictApiFieldExtractor, \
    ListApiFieldExtractor
from nlp.extractor.output import NoneOutput, StringOutput
from nlp.generate.argument import Kwarg
from nlp.generate.attribute import Attribute
from nlp.generate.pytest import PyTestModelFactoryExpression
from nlp.generate.pytest.suite import PyTestTestSuite
from nlp.generate.statement import AssignmentStatement
from nlp.generate.variable import Variable
from nlp.generate.warning import GenerationWarning
from nlp.setup import Nlp
from test_utils import assert_callable_raises

suite = PyTestTestSuite('bar')
default_test_case = suite.create_and_add_test_case('foo')
field = AbstractApiFieldAdapter('name')
nlp = Nlp.for_language(Languages.DE)
document = nlp('Sie hat 3 Äpfel.')


@pytest.mark.parametrize(
    'value, expected_value', [
        ('1', 1),
        ('Wahr', True),
        ('False', False),
        ('falsch', False),
        ('0.33', 0.33),
        ('Some string', 'Some string'),
        ('"Some string"', 'Some string'),
        ('\'Some string\'', 'Some string'),
    ]
)
def test_rest_field_extractor_extract_string(value, expected_value):
    """Check that the rest field extractor can still handle strings as source."""
    extractor = ApiModelFieldExtractor(default_test_case, value, field, document)
    assert extractor.extract_value() == expected_value
    assert type(extractor.extract_value()) == type(expected_value)
    assert extractor.field_name == field.name


@pytest.mark.parametrize(
    'doc, token_index, expected_value', [
        (nlp('Gegeben sei ein Benutzer der Admin ist'), 5, True),
        (nlp('Gegeben sei ein Benutzer der kein Admin ist'), 6, False),
        (nlp('Gegeben sei ein Benutzer der Fußball spielt'), 5, True),
        (nlp('Gegeben sei ein Benutzer der kein Fußball spielt'), 6, False),
        (nlp('Gegeben sei ein Benutzer der nicht Fußball spielt'), 6, False),
    ]
)
def test_rest_boolean_extractor(doc, token_index, expected_value):
    """Check that booleans are handled correctly."""
    extractor = BooleanApiModelFieldExtractor(default_test_case, doc[token_index], field, doc)
    assert extractor.extract_value() == expected_value


@pytest.mark.parametrize(
    'doc, token_index, expected_value', [
        (nlp('Gegeben sei ein Benutzer mit dem Alter 12'), 6, 12),
        (nlp('Gegeben sei ein Benutzer mit dem Alter Alice'), 6, GenerationWarning('')),
        (nlp('Gegeben sei ein Dach mit der Länge 13'), 6, 13),
        (nlp('Gegeben sei ein Dach mit der Länge "3"'), 6, 3),
    ]
)
def test_rest_int_extractor(doc, token_index, expected_value):
    """Check that ints are handled correctly"""
    extractor = IntegerApiModelFieldExtractor(default_test_case, doc[token_index], field, doc)
    if isinstance(expected_value, GenerationWarning):
        assert isinstance(extractor.extract_value(), GenerationWarning)
    else:
        assert extractor.extract_value() == expected_value


@pytest.mark.parametrize(
    'doc, token_index, expected_value', [
        (nlp('Gegeben sei ein Benutzer mit dem Alter 12'), 6, 12),
        (nlp('Gegeben sei ein Benutzer mit dem Alter Alice'), 6, GenerationWarning('')),
        (nlp('Gegeben sei ein Dach mit der Länge 13'), 6, 13),
        (nlp('Gegeben sei ein Dach mit der Länge "3.123"'), 6, 3.123),
    ]
)
def test_rest_float_extractor(doc, token_index, expected_value):
    """Check that floats are handled correctly"""
    extractor = FloatApiModelFieldExtractor(default_test_case, doc[token_index], field, doc)
    if isinstance(expected_value, GenerationWarning):
        assert isinstance(extractor.extract_value(), GenerationWarning)
    else:
        assert extractor.extract_value() == expected_value


@pytest.mark.parametrize(
    'doc, token_index', [
        (nlp('Gegeben sei ein Benutzer der Fußball spielt.'), 6),
        (nlp('Gegeben sei ein Benutzer der nicht Fußball spielt.'), 7),
        (nlp('Gegeben sei ein Benutzer der groß ist.'), 5),  # adv
        (nlp('Gegeben sei ein Benutzer der nicht groß ist.'), 6),
        (nlp('Gegeben sei ein Benutzer mit dem Namen Alice'), 6),
        (nlp('Gegeben sei ein Benutzer mit der Nummer 7'), 6),
        (nlp('Gegeben sei ein Benutzer mit der Frisur "abcdef"'), 6),
        (nlp('Gegeben sei ein Benutzer mit Alice als Namen'), 7),
    ]
)
def test_rest_none_extractor(doc, token_index):
    """Check that none is always returned."""
    extractor = NoneApiModelFieldExtractor(default_test_case, doc[token_index], field, doc)
    assert extractor.extract_value() is None


@pytest.mark.parametrize(
    'doc, token_index, expected_value', [
        (nlp('Gegeben sei ein Benutzer mit dem Namen Franz'), 6, 'Franz'),
        (nlp('Gegeben sei ein Dach mit der Länge 2'), 6, '2'),
        (nlp('Gegeben sei ein Auftrag mit dem Typen "ABCD"'), 6, 'ABCD'),
        (nlp('Gegeben sei ein Benutzer der Fußball spielt.'), 6, 'True'),
    ]
)
def test_rest_string_extractor(doc, token_index, expected_value):
    """Check that a string is always returned."""
    extractor = StringApiModelFieldExtractor(default_test_case, doc[token_index], field, doc)
    assert extractor.extract_value() == expected_value\


@pytest.mark.parametrize(
    'doc, token_index, expected_value', [
        (nlp('Gegeben sei ein Benutzer mit dem Namen "{\'1\': 123}"'), 6, {'1': 123}),
        (nlp('Gegeben sei ein Benutzer mit dem Namen Alice'), 6, GenerationWarning),
    ]
)
def test_rest_dict_extractor(doc, token_index, expected_value):
    """Check that a dict is always returned."""
    extractor = DictApiFieldExtractor(default_test_case, doc[token_index], field, doc)
    if expected_value == GenerationWarning:
        assert isinstance(extractor.extract_value(), GenerationWarning)
    else:
        assert extractor.extract_value() == expected_value


def test_model_field_get_output_class():
    """Check that the model api field extractor determines the output class correctly."""
    field_read_only = AbstractApiFieldAdapter('name')
    field_read_only.read_only = True

    extractor = ModelApiFieldExtractor(default_test_case, document[1], field_read_only, document)
    assert extractor.get_output_class() == NoneOutput

    field_valid = AbstractApiFieldAdapter('name_2')
    field_valid.model_field = CharField(max_length=10)
    extractor = ModelApiFieldExtractor(default_test_case, document[1], field_valid, document)
    assert extractor.get_output_class() == StringOutput


@pytest.mark.parametrize(
    'doc, token_index, expected_value', [
        (nlp('Wenn Alice den ToDo "Bob" hinzufügt'), 3, Variable('', '')),
        (nlp('Wenn Alice den ToDo 1 hinzufügt'), 3, 1),
        (nlp('Wenn Alice den ToDo "blubb" hinzufügt'), 3, "blubb"),
    ]
)
def test_fk_rest_extractor(doc, token_index, expected_value):
    """Check that the fk extractor really gets the correct value."""
    test_suite = PyTestTestSuite('bar')
    test_case = test_suite.create_and_add_test_case('qweqwe')
    var = Variable('Bob', 'ToDo')
    test_case.add_statement(AssignmentStatement(
        expression=PyTestModelFactoryExpression(ModelAdapter(ToDo, None), [Kwarg('bar', 123)]),
        variable=var,  # <-- variable defined
    ))

    fk_field = ApiFieldAdapter(serializers.PrimaryKeyRelatedField(queryset=ToDo.objects.all()))
    extractor = ForeignKeyApiFieldExtractor(test_case, doc[token_index], fk_field, doc)
    extracted_value = extractor.extract_value()

    if isinstance(expected_value, Variable):
        assert isinstance(extracted_value, Attribute)
        assert extracted_value.variable == var
        assert extracted_value.attribute_name == 'pk'
    else:
        assert extracted_value == expected_value
