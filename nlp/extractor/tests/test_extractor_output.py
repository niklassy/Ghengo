import pytest
from django.contrib.auth.models import User

from core.constants import Languages
from django_meta.model import ModelWrapper
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
from nlp.utils import NoToken
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
def test_extractor_output_python_source(value, output):
    """Check if guessing the input works as expected."""
    extractor_output = ExtractorOutput(value, document)
    guessed_value = extractor_output.get_output()
    if isinstance(output, Variable):
        assert isinstance(guessed_value, Variable)
    else:
        assert guessed_value == output
    assert isinstance(extractor_output.output_token, NoToken)


@pytest.mark.parametrize(
    'doc, token_index, expected_output, source_output_index', [
        (nlp('Gegeben sei ein Benutzer der Fußball spielt.'), 6, True, 6),  # verb
        (nlp('Gegeben sei ein Benutzer der nicht Fußball spielt.'), 7, False, 7),  # verb
        (nlp('Gegeben sei ein Benutzer der groß ist.'), 5, True, 6),  # adv
        (nlp('Gegeben sei ein Benutzer der nicht groß ist.'), 6, False, 7),  # adv
        (nlp('Gegeben sei ein erfahrener Benutzer.'), 3, True, 3),  # adj
        (nlp('Gegeben sei ein nicht erfahrener Benutzer.'), 4, False, 4),  # adj
        (nlp('Gegeben sei ein Benutzer mit dem Namen Alice'), 6, 'Alice', 7),
        (nlp('Gegeben sei ein Benutzer mit dem Namen "Alice"'), 6, 'Alice', 7),
        (nlp('Gegeben sei ein Benutzer mit der Nummer 7'), 6, 7, 7),
        (nlp('Gegeben sei ein Benutzer mit der Frisur "abcdef"'), 6, 'abcdef', 7),
        (nlp('Gegeben sei ein Benutzer mit Alice als Namen'), 7, 'Alice', 5),  # in prev noun chunk
    ]
)
def test_extractor_output_token_source(doc, token_index, expected_output, source_output_index):
    """Check if the correct string is extracted given a specific token."""
    extractor_output = ExtractorOutput(doc[token_index], doc)
    actual_output = extractor_output.get_output()
    assert expected_output == actual_output
    extractor_output.source_represents_output = True
    assert extractor_output.output_token == doc[source_output_index]


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
    assert not extractor_output.output_token


@pytest.mark.parametrize(
    'doc, token_index, expected_output, source_output_index', [
        (nlp('Gegeben sei ein Benutzer mit dem Namen Franz'), 6, 'Franz', 7),
        (nlp('Gegeben sei ein Dach mit der Länge 2'), 6, '2', 7),
        (nlp('Gegeben sei ein Auftrag mit dem Typen "ABCD"'), 6, 'ABCD', 7),
        (nlp('Gegeben sei ein Auftrag mit dem Typen "<my_type>"'), 6, Variable('my_type', ''), 7),
        (nlp('Gegeben sei ein Benutzer der Fußball spielt.'), 6, 'True', 6),
    ]
)
def test_string_extractor_output_doc(doc, token_index, expected_output, source_output_index):
    """Test if the string output always returns stringifies the output."""
    extractor_output = StringOutput(doc[token_index], doc)
    if isinstance(expected_output, Variable):
        assert isinstance(extractor_output.get_output(), Variable)
        assert extractor_output.get_output().name_predetermined == expected_output.name_predetermined
    else:
        assert extractor_output.get_output() == expected_output
    assert extractor_output.output_token == doc[source_output_index]


@pytest.mark.parametrize(
    'source, expected_output', [
        ('1', '1'),
        (1, '1'),
        ('Hallo Test', 'Hallo Test'),
        ('"blubb"', 'blubb'),
        ('<test>', Variable('test', '')),
        ('{"1": 12}', "{'1': 12}"),
        ('[1, 2]', "[1, 2]"),
        ('(1, 2)', "(1, 2)"),
    ]
)
def test_string_extractor_output_python_source(source, expected_output):
    """Check that the string output handles python sources correctly."""
    extractor_output = StringOutput(source, document)
    actual_output = extractor_output.get_output()

    assert not extractor_output.output_token
    if isinstance(expected_output, Variable):
        assert isinstance(extractor_output.get_output(), Variable)
        assert extractor_output.get_output().name_predetermined == expected_output.name_predetermined
    else:
        assert actual_output == expected_output


@pytest.mark.parametrize(
    'doc, token_index, expected_output, raises', [
        (nlp('Gegeben sei ein Benutzer mit dem Namen "{\'1\': 123}"'), 6, {'1': 123}, False),
        (nlp('Gegeben sei ein Benutzer mit dem Namen "<name>"'), 6, Variable('name', ''), False),
        (nlp('Gegeben sei ein Benutzer mit dem Namen Alice'), 6, None, True),
    ]
)
def test_dict_extractor_output_doc_source(doc, token_index, expected_output, raises):
    """Test if the dict output always returns a dictionary or an error."""
    extractor_output = DictOutput(doc[token_index], doc)

    if not raises:
        if isinstance(expected_output, Variable):
            assert isinstance(extractor_output.get_output(), Variable)
            assert extractor_output.get_output().name_predetermined == expected_output.name_predetermined
        else:
            assert extractor_output.get_output() == expected_output
    else:
        assert_callable_raises(extractor_output.get_output, ExtractionError)


@pytest.mark.parametrize(
    'source, expected_output, raises', [
        ('{"1": 12}', {"1": 12}, False),
        ('1', None, True),
        (1, None, True),
        ('[1, 2]', None, True),
        ('Alice', None, True),
    ]
)
def test_dict_extractor_output_python_source(source, expected_output, raises):
    """Check that the dict output handles python sources as expected."""
    extractor_output = DictOutput(source, document)

    if not raises:
        if isinstance(expected_output, Variable):
            assert isinstance(extractor_output.get_output(), Variable)
            assert extractor_output.get_output().name_predetermined == expected_output.name_predetermined
        else:
            assert extractor_output.get_output() == expected_output
    else:
        assert_callable_raises(extractor_output.get_output, ExtractionError)


@pytest.mark.parametrize(
    'doc, token_index, expected_output, raises, source_output_index', [
        (nlp('Gegeben sei ein Benutzer mit dem Alter 12'), 6, '12', False, 7),
        (nlp('Ich suche den zweiten Eintrag'), 4, '2', False, 3),
        (nlp('Gegeben seien zwei Einträge'), 3, '2', False, 2),
        (nlp('Gegeben sei ein Benutzer mit dem Alter "12"'), 6, '12', False, 7),
        (nlp('Gegeben sei ein Benutzer mit dem Alter Alice'), 6, None, True, None),
        (nlp('Gegeben sei ein Dach mit der Länge 13'), 6, '13', False, 7),
        (nlp('Gegeben sei ein Dach mit der Länge "<length>"'), 6, Variable('length', ''), False, 7),
        (nlp('Gegeben sei ein Dach mit der Länge "3.123"'), 6, '3.123', False, 7),
    ]
)
def test_number_as_string_output_doc_source(doc, token_index, expected_output, raises, source_output_index):
    """Check if numbers are extracted correctly and returned as a string."""
    extractor_output = NumberAsStringOutput(doc[token_index], doc)

    if not raises:
        if isinstance(expected_output, Variable):
            assert isinstance(extractor_output.get_output(), Variable)
            assert extractor_output.get_output().name_predetermined == expected_output.name_predetermined
        else:
            assert extractor_output.get_output() == expected_output
        assert extractor_output.output_token == doc[source_output_index]
    else:
        assert_callable_raises(extractor_output.get_output, ExtractionError)


@pytest.mark.parametrize(
    'source, expected_output, raises', [
        ('1', '1', False),
        ('"<test>"', Variable('test', ''), False),
        ('3.22', '3.22', False),
        (1, '1', False),
        ('[1, 2]', None, True),
        ('Alice', None, True),
        ('{"1": 12}', {"1": 12}, True),
    ]
)
def test_dict_extractor_output_python_source(source, expected_output, raises):
    """Check that the dict output handles python sources as expected."""
    extractor_output = NumberAsStringOutput(source, document)

    if not raises:
        if isinstance(expected_output, Variable):
            assert isinstance(extractor_output.get_output(), Variable)
            assert extractor_output.get_output().name_predetermined == expected_output.name_predetermined
        else:
            assert extractor_output.get_output() == expected_output
    else:
        assert_callable_raises(extractor_output.get_output, ExtractionError)


@pytest.mark.parametrize(
    'doc, token_index, expected_output, raises, source_output_index', [
        (nlp('Gegeben sei ein Benutzer mit dem Alter 12'), 6, 12, False, 7),
        (nlp('Gegeben seien zwei Benutzer'), 3, 2, False, 2),
        (nlp('Gegeben sei der zweite Benutzer'), 4, 2, False, 3),
        (nlp('Gegeben sei ein Benutzer mit dem Alter Alice'), 6, None, True, None),
        (nlp('Gegeben sei ein Dach mit der Länge 13'), 6, 13, False, 7),
        (nlp('Gegeben sei ein Dach mit der Länge "<length>"'), 6, Variable('length', ''), False, 7),
        (nlp('Gegeben sei ein Dach mit der Länge "3"'), 6, 3, False, 7),
    ]
)
def test_integer_extractor_output_doc_source(doc, token_index, expected_output, raises, source_output_index):
    """Check if integers are extracted correctly."""
    extractor_output = IntegerOutput(doc[token_index], doc)

    if not raises:
        if isinstance(expected_output, Variable):
            assert isinstance(extractor_output.get_output(), Variable)
            assert extractor_output.get_output().name_predetermined == expected_output.name_predetermined
        else:
            assert extractor_output.get_output() == expected_output
        assert extractor_output.output_token == doc[source_output_index]
    else:
        assert_callable_raises(extractor_output.get_output, ExtractionError)


@pytest.mark.parametrize(
    'source, expected_output, raises', [
        ('1', 1, False),
        ('"<test>"', Variable('test', ''), False),
        ('3.22', 3, False),
        (1, 1, False),
        ('[1, 2]', None, True),
        ('Alice', None, True),
        ('{"1": 12}', {"1": 12}, True),
    ]
)
def test_integer_extractor_output_python_source(source, expected_output, raises):
    """Check that the dict output handles python sources as expected."""
    extractor_output = IntegerOutput(source, document)

    if not raises:
        if isinstance(expected_output, Variable):
            assert isinstance(extractor_output.get_output(), Variable)
            assert extractor_output.get_output().name_predetermined == expected_output.name_predetermined
        else:
            assert extractor_output.get_output() == expected_output
    else:
        assert_callable_raises(extractor_output.get_output, ExtractionError)


@pytest.mark.parametrize(
    'doc, token_index, expected_output, raises, source_output_index', [
        (nlp('Gegeben sei ein Benutzer mit dem Alter 12'), 6, 12, False, 7),
        (nlp('Gegeben seien zwei Benutzer'), 3, 2, False, 2),
        (nlp('Gegeben sei der zweite Benutzer'), 4, 2, False, 3),
        (nlp('Gegeben sei ein Benutzer mit dem Alter Alice'), 6, None, True, None),
        (nlp('Gegeben sei ein Dach mit der Länge 13'), 6, 13, False, 7),
        (nlp('Gegeben sei ein Dach mit der Länge "3.123"'), 6, 3.123, False, 7),
    ]
)
def test_float_extractor_output_doc_source(doc, token_index, expected_output, raises, source_output_index):
    """Check if floats are extracted correctly."""
    extractor_output = FloatOutput(doc[token_index], doc)

    if not raises:
        assert extractor_output.get_output() == expected_output
        assert extractor_output.output_token == doc[source_output_index]
    else:
        assert_callable_raises(extractor_output.get_output, ExtractionError)


@pytest.mark.parametrize(
    'source, expected_output, raises', [
        ('1', 1, False),
        ('"<asd>"', Variable('asd', ''), False),
        ('3.22', 3.22, False),
        (1, 1, False),
        ('[1, 2]', None, True),
        ('Alice', None, True),
        ('{"1": 12}', {"1": 12}, True),
    ]
)
def test_float_extractor_output_python_source(source, expected_output, raises):
    """Check that the float output handles python sources as expected."""
    extractor_output = FloatOutput(source, document)

    if not raises:
        if isinstance(expected_output, Variable):
            assert isinstance(extractor_output.get_output(), Variable)
            assert extractor_output.get_output().name_predetermined == expected_output.name_predetermined
        else:
            assert extractor_output.get_output() == expected_output
    else:
        assert_callable_raises(extractor_output.get_output, ExtractionError)


@pytest.mark.parametrize(
    'doc, token_index, expected_output, source_output_index', [
        (nlp('Gegeben sei ein Benutzer der Admin ist'), 5, True, 1),
        (nlp('Gegeben sei ein Benutzer der kein Admin ist'), 6, False, 7),
        (nlp('Gegeben sei ein Benutzer der "<is_admin>" ist'), 5, Variable('is_admin', ''), 5),
        (nlp('Gegeben sei ein Benutzer der Fußball spielt'), 5, True, 1),
        (nlp('Gegeben sei ein Benutzer der kein Fußball spielt'), 6, False, 7),
        (nlp('Gegeben sei ein Benutzer der nicht Fußball spielt.'), 6, False, 7),
        (nlp('Gegeben sei ein Benutzer der nicht Fußball spielt'), 6, False, 1),
    ]
)
def test_bool_extractor_output_doc_source(doc, token_index, expected_output, source_output_index):
    """Check if floats are extracted correctly."""
    extractor_output = BooleanOutput(doc[token_index], doc)
    assert extractor_output.get_output() == expected_output
    assert extractor_output.output_token == doc[source_output_index]


@pytest.mark.parametrize(
    'source, expected_output, raises', [
        (True, True, False),
        (False, False, False),
        ('1', True, False),
        ('0', False, False),
        ('true', True, False),
        ('false', False, False),
        ('ja', True, False),
        ('asdasd', False, False),
        ('<test>', Variable('test', ''), False),
    ]
)
def test_float_extractor_output_python_source(source, expected_output, raises):
    """Check that the float output handles python sources as expected."""
    extractor_output = BooleanOutput(source, document)

    if not raises:
        if isinstance(expected_output, Variable):
            assert isinstance(extractor_output.get_output(), Variable)
            assert extractor_output.get_output().name_predetermined == expected_output.name_predetermined
        else:
            assert extractor_output.get_output() == expected_output
    else:
        assert_callable_raises(extractor_output.get_output, ExtractionError)


@pytest.mark.parametrize(
    'doc, token_index, raises, source_output_index, variable_in_text', [
        (nlp('Gegeben sei ein Benutzer der Bob als Freund hat'), 7, False, 5, None),
        (nlp('Gegeben sei ein Benutzer der Alice als Freund hat'), 7, True, 5, None),
        (nlp('Gegeben sei ein Benutzer der den Freund Bob hat'), 6, False, 7, None),
        (nlp('Gegeben sei ein Benutzer der den Freund "<friend>" hat'), 6, False, 7, Variable('friend', '')),
        (nlp('Gegeben sei ein Benutzer der den Freund "Bob" hat'), 6, False, 7, None),
        (nlp('Gegeben sei ein Benutzer der den Freund asdasdasd hat'), 6, True, None, None),
    ]
)
def test_variable_extractor_output_doc_source(doc, token_index, raises, source_output_index, variable_in_text):
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
        output = extractor_output.get_output()
        assert isinstance(output, Variable)
        if variable_in_text:
            assert output.name_predetermined == variable_in_text.name_predetermined
            assert output != var
        else:
            assert output == var
        assert extractor_output.output_token == doc[source_output_index]
    else:
        assert_callable_raises(extractor_output.get_output, ExtractionError)


@pytest.mark.parametrize(
    'source, expected_output, raises', [
        ('<test>', Variable('test', ''), False),
        ('123', None, True),
        (123, None, True),
        ('[1, 2]', None, True),
        ('Alice', None, True),
    ]
)
def test_variable_extractor_output_python_source(source, expected_output, raises):
    """Check that the float output handles python sources as expected."""
    suite = PyTestTestSuite('bar')
    test_case = suite.create_and_add_test_case('qweqwe')
    extractor_output = VariableOutput(source, document, test_case)

    if not raises:
        if isinstance(expected_output, Variable):
            assert isinstance(extractor_output.get_output(), Variable)
            assert extractor_output.get_output().name_predetermined == expected_output.name_predetermined
        else:
            assert extractor_output.get_output() == expected_output
    else:
        assert_callable_raises(extractor_output.get_output, ExtractionError)


@pytest.mark.parametrize(
    'doc, token_index, raises, model_input, source_output_index, variable_in_text', [
        (nlp('Gegeben sei ein Benutzer der Bob als Freund hat'), 7, False, User, 5, None),
        (nlp('Gegeben sei ein Benutzer der Bob als Freund hat'), 7, True, Order, None, None),   # <- wrong model
        (nlp('Gegeben sei ein Benutzer der Alice als Freund hat'), 7, True, User, None, None),
        (nlp('Gegeben sei ein Benutzer der den Freund Bob hat'), 6, False, User, 7, None),
        (nlp('Gegeben sei ein Benutzer der den Freund "<friend>" hat'), 6, False, User, 7, Variable('friend', '')),
        (nlp('Gegeben sei ein Benutzer der den Freund "Bob" hat'), 6, False, User, 7, None),
        (nlp('Gegeben sei ein Benutzer der den Freund "Bob" hat'), 6, True, Order, None, None),        # <- wrong model
        (nlp('Gegeben sei ein Benutzer der den Freund asdasdasd hat'), 6, True, User, None, None),
    ]
)
def test_model_variable_extractor_output(doc, token_index, raises, model_input, source_output_index, variable_in_text):
    """Check if variables are handled correctly."""
    suite = PyTestTestSuite('bar')
    test_case = suite.create_and_add_test_case('qweqwe')
    var = Variable('Bob', 'User')
    test_case.add_statement(AssignmentStatement(
        expression=PyTestModelFactoryExpression(ModelWrapper(User, None), [Kwarg('bar', 123)]),
        variable=var,  # <-- variable defined
    ))

    extractor_output = ModelVariableOutput(doc[token_index], doc, test_case, model_input)
    if not raises:
        output = extractor_output.get_output()
        assert isinstance(output, Variable)

        if variable_in_text:
            assert output.name_predetermined == variable_in_text.name_predetermined
            assert output != var
        else:
            assert output == var
        assert extractor_output.output_token == doc[source_output_index]
    else:
        assert_callable_raises(extractor_output.get_output, ExtractionError)
