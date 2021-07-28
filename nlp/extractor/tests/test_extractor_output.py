import pytest
from django.contrib.auth.models import User

from core.constants import Languages
from django_meta.model import ModelAdapter
from django_sample_project.apps.order.models import Order
from nlp.extractor.exception import ExtractionError
from nlp.extractor.output import ExtractorOutput, NoneOutput, StringOutput, DictOutput, NumberAsStringOutput, \
    IntegerOutput, FloatOutput, BooleanOutput, VariableOutput, ModelVariableOutput
from nlp.generate.argument import Kwarg
from nlp.generate.expression import Expression
from nlp.generate.pytest import PyTestModelFactoryExpression
from nlp.generate.pytest.suite import PyTestTestSuite
from nlp.generate.statement import AssignmentStatement
from nlp.generate.variable import Variable
from nlp.setup import Nlp
from test_utils import assert_callable_raises

nlp = Nlp.for_language(Languages.DE)
document = nlp('Sie hat 3 Äpfel.')


@pytest.mark.parametrize(
    'value, output', [
        ('1', 1),
        (1, 1),
        (True, True),
        ('asd', 'asd'),
        ('"asd"', 'asd'),
        ('"<asd>"', Variable('asd', '')),
        ('Wahr', True),
        ('{"1": 12}', {'1': 12}),
        ('[1, 2]', [1, 2]),
        ('(1, 2)', (1, 2)),
    ]
)
def test_extractor_output_guess_output_type(value, output):
    """Check if guessing the input works as expected."""
    extractor_output = ExtractorOutput(value, document)
    guessed_value = extractor_output.guess_output_type(value)
    if isinstance(output, Variable):
        assert isinstance(guessed_value, Variable)
    else:
        assert guessed_value == output
    assert extractor_output.output_source == value


@pytest.mark.parametrize(
    'doc, token_index, expected_output, source_output_index', [
        (nlp('Gegeben sei ein Benutzer der Fußball spielt.'), 6, True, 6),  # verb
        (nlp('Gegeben sei ein Benutzer der nicht Fußball spielt.'), 7, False, 7),  # verb
        (nlp('Gegeben sei ein Benutzer der groß ist.'), 5, True, 5),  # adv
        (nlp('Gegeben sei ein Benutzer der nicht groß ist.'), 6, False, 6),  # adv
        (nlp('Gegeben sei ein erfahrener Benutzer.'), 3, True, 3),  # adj
        (nlp('Gegeben sei ein nicht erfahrener Benutzer.'), 4, False, 4),  # adj
        (nlp('Gegeben sei ein Benutzer mit dem Namen Alice'), 6, 'Alice', 6),
        (nlp('Gegeben sei ein Benutzer mit der Nummer 7'), 6, '7', 6),
        (nlp('Gegeben sei ein Benutzer mit der Frisur "abcdef"'), 6, '"abcdef"', 6),
        (nlp('Gegeben sei ein Benutzer mit Alice als Namen'), 7, 'Alice', 7),  # in prev noun chunk
    ]
)
def test_extractor_output_token_to_string_output(doc, token_index, expected_output, source_output_index):
    """Check if the correct string is extracted given a specific token."""
    extractor_output = ExtractorOutput(doc[token_index], doc)
    actual_output = extractor_output.token_to_string_output(extractor_output.source)
    assert expected_output == actual_output
    extractor_output.source_represents_output = True
    assert extractor_output.token_to_string_output(extractor_output.source) == str(extractor_output.source)
    assert extractor_output.output_source == doc[source_output_index]


@pytest.mark.parametrize(
    'doc, token_index', [
        (nlp('Gegeben sei ein Benutzer der Fußball spielt.'), 6),  # verb
        (nlp('Gegeben sei ein Benutzer der nicht Fußball spielt.'), 7),  # verb
        (nlp('Gegeben sei ein Benutzer der groß ist.'), 5),  # adv
        (nlp('Gegeben sei ein Benutzer der nicht groß ist.'), 6),  # adv
        (nlp('Gegeben sei ein erfahrener Benutzer.'), 3),  # adj
        (nlp('Gegeben sei ein Benutzer mit dem Namen Alice'), 6),
        (nlp('Gegeben sei ein Benutzer mit der Nummer 7'), 6),
        (nlp('Gegeben sei ein Benutzer mit der Frisur "abcdef"'), 6),
        (nlp('Gegeben sei ein Benutzer mit Alice als Namen'), 7),  # in prev noun chunk
    ]
)
def test_none_extractor_output(doc, token_index):
    """Test if the none output always returns None."""
    extractor_output = NoneOutput(doc[token_index], doc)
    assert extractor_output.get_output() is None
    assert extractor_output.output_source is None


@pytest.mark.parametrize(
    'doc, token_index, expected_output, source_output_index', [
        (nlp('Gegeben sei ein Benutzer mit dem Namen Franz'), 6, 'Franz', 7),
        (nlp('Gegeben sei ein Dach mit der Länge 2'), 6, '2', 7),
        (nlp('Gegeben sei ein Auftrag mit dem Typen "ABCD"'), 6, 'ABCD', 7),
        (nlp('Gegeben sei ein Benutzer der Fußball spielt.'), 6, 'True', 6),
    ]
)
def test_string_extractor_output(doc, token_index, expected_output, source_output_index):
    """Test if the string output always returns stringifies the output."""
    extractor_output = StringOutput(doc[token_index], doc)
    assert extractor_output.get_output() == expected_output
    assert extractor_output.output_source == doc[source_output_index]


@pytest.mark.parametrize(
    'doc, token_index, expected_output, raises', [
        (nlp('Gegeben sei ein Benutzer mit dem Namen "{\'1\': 123}"'), 6, {'1': 123}, False),
        (nlp('Gegeben sei ein Benutzer mit dem Namen Alice'), 6, None, True),
    ]
)
def test_dict_extractor_output(doc, token_index, expected_output, raises):
    """Test if the dict output always returns a dictionary or an error."""
    extractor_output = DictOutput(doc[token_index], doc)

    if not raises:
        assert extractor_output.get_output() == expected_output
    else:
        assert_callable_raises(extractor_output.get_output, ExtractionError)


@pytest.mark.parametrize(
    'doc, token_index, expected_output, raises, source_output_index', [
        (nlp('Gegeben sei ein Benutzer mit dem Alter 12'), 6, '12', False, 7),
        (nlp('Gegeben sei ein Benutzer mit dem Alter Alice'), 6, None, True, None),
        (nlp('Gegeben sei ein Dach mit der Länge 13'), 6, '13', False, 7),
        (nlp('Gegeben sei ein Dach mit der Länge "3.123"'), 6, '3.123', False, 7),
    ]
)
def test_number_as_string_output(doc, token_index, expected_output, raises, source_output_index):
    """Check if numbers are extracted correctly and returned as a string."""
    extractor_output = NumberAsStringOutput(doc[token_index], doc)

    if not raises:
        assert extractor_output.get_output() == expected_output
        assert extractor_output.output_source == doc[source_output_index]
    else:
        assert_callable_raises(extractor_output.get_output, ExtractionError)


@pytest.mark.parametrize(
    'doc, token_index, expected_output, raises, source_output_index', [
        (nlp('Gegeben sei ein Benutzer mit dem Alter 12'), 6, 12, False, 7),
        (nlp('Gegeben sei ein Benutzer mit dem Alter Alice'), 6, None, True, None),
        (nlp('Gegeben sei ein Dach mit der Länge 13'), 6, 13, False, 7),
        (nlp('Gegeben sei ein Dach mit der Länge "3"'), 6, 3, False, 7),
    ]
)
def test_integer_extractor_output(doc, token_index, expected_output, raises, source_output_index):
    """Check if integers are extracted correctly."""
    extractor_output = IntegerOutput(doc[token_index], doc)

    if not raises:
        assert extractor_output.get_output() == expected_output
        assert extractor_output.output_source == doc[source_output_index]
    else:
        assert_callable_raises(extractor_output.get_output, ExtractionError)


@pytest.mark.parametrize(
    'doc, token_index, expected_output, raises, source_output_index', [
        (nlp('Gegeben sei ein Benutzer mit dem Alter 12'), 6, 12, False, 7),
        (nlp('Gegeben sei ein Benutzer mit dem Alter Alice'), 6, None, True, None),
        (nlp('Gegeben sei ein Dach mit der Länge 13'), 6, 13, False, 7),
        (nlp('Gegeben sei ein Dach mit der Länge "3.123"'), 6, 3.123, False, 7),
    ]
)
def test_float_extractor_output(doc, token_index, expected_output, raises, source_output_index):
    """Check if floats are extracted correctly."""
    extractor_output = FloatOutput(doc[token_index], doc)

    if not raises:
        assert extractor_output.get_output() == expected_output
        assert extractor_output.output_source == doc[source_output_index]
    else:
        assert_callable_raises(extractor_output.get_output, ExtractionError)


@pytest.mark.parametrize(
    'doc, token_index, expected_output, source_output_index', [
        (nlp('Gegeben sei ein Benutzer der Admin ist'), 5, True, 1),
        (nlp('Gegeben sei ein Benutzer der kein Admin ist'), 6, False, 7),
        (nlp('Gegeben sei ein Benutzer der Fußball spielt'), 5, True, 1),
        (nlp('Gegeben sei ein Benutzer der kein Fußball spielt'), 6, False, 7),
        (nlp('Gegeben sei ein Benutzer der nicht Fußball spielt.'), 6, False, 7),
        (nlp('Gegeben sei ein Benutzer der nicht Fußball spielt'), 6, False, 1),
    ]
)
def test_bool_extractor_output(doc, token_index, expected_output, source_output_index):
    """Check if floats are extracted correctly."""
    extractor_output = BooleanOutput(doc[token_index], doc)
    assert extractor_output.get_output() == expected_output
    assert extractor_output.output_source == doc[source_output_index]


@pytest.mark.parametrize(
    'doc, token_index, raises, source_output_index', [
        (nlp('Gegeben sei ein Benutzer der Bob als Freund hat'), 7, False, 5),
        (nlp('Gegeben sei ein Benutzer der Alice als Freund hat'), 7, True, 5),
        (nlp('Gegeben sei ein Benutzer der den Freund Bob hat'), 6, False, 7),
        (nlp('Gegeben sei ein Benutzer der den Freund "Bob" hat'), 6, False, 7),
        (nlp('Gegeben sei ein Benutzer der den Freund asdasdasd hat'), 6, True, None),
    ]
)
def test_variable_extractor_output(doc, token_index, raises, source_output_index):
    """Check if variables are handled correctly."""
    suite = PyTestTestSuite('bar')
    test_case = suite.create_and_add_test_case('qweqwe')
    var = Variable('Bob', 'Order')
    test_case.add_statement(AssignmentStatement(
        expression=Expression(),
        variable=var,  # <-- variable defined
    ))

    extractor_output = VariableOutput(doc[token_index], doc, test_case)
    if not raises:
        assert isinstance(extractor_output.get_output(), Variable)
        assert extractor_output.get_output() == var
        assert extractor_output.output_source == doc[source_output_index]
    else:
        assert_callable_raises(extractor_output.get_output, ExtractionError)


@pytest.mark.parametrize(
    'doc, token_index, raises, model_input, source_output_index', [
        (nlp('Gegeben sei ein Benutzer der Bob als Freund hat'), 7, False, User, 5),
        (nlp('Gegeben sei ein Benutzer der Bob als Freund hat'), 7, True, Order, None),   # <- wrong model
        (nlp('Gegeben sei ein Benutzer der Alice als Freund hat'), 7, True, User, None),
        (nlp('Gegeben sei ein Benutzer der den Freund Bob hat'), 6, False, User, 7),
        (nlp('Gegeben sei ein Benutzer der den Freund "Bob" hat'), 6, False, User, 7),
        (nlp('Gegeben sei ein Benutzer der den Freund "Bob" hat'), 6, True, Order, None),        # <- wrong model
        (nlp('Gegeben sei ein Benutzer der den Freund asdasdasd hat'), 6, True, User, None),
    ]
)
def test_model_variable_extractor_output(doc, token_index, raises, model_input, source_output_index):
    """Check if variables are handled correctly."""
    suite = PyTestTestSuite('bar')
    test_case = suite.create_and_add_test_case('qweqwe')
    var = Variable('Bob', 'User')
    test_case.add_statement(AssignmentStatement(
        expression=PyTestModelFactoryExpression(ModelAdapter(User, None), [Kwarg('bar', 123)]),
        variable=var,  # <-- variable defined
    ))

    extractor_output = ModelVariableOutput(doc[token_index], doc, test_case, model_input)
    if not raises:
        assert isinstance(extractor_output.get_output(), Variable)
        assert extractor_output.get_output() == var
        assert extractor_output.output_source == doc[source_output_index]
    else:
        assert_callable_raises(extractor_output.get_output, ExtractionError)
