import pytest

from core.constants import Languages
from django_meta.project import DjangoProject
from gherkin.ast import Given
from nlp.converter.request import RequestConverter
from nlp.converter.response import ResponseConverterBase, ManyCheckEntryResponseConverter, ManyLengthResponseConverter, \
    ManyResponseConverter, ResponseConverter, ResponseStatusCodeConverter, ResponseErrorConverter

from nlp.generate.pytest.suite import PyTestTestSuite
from nlp.generate.warning import GenerationWarning
from nlp.setup import Nlp
from nlp.tests.utils import MockTranslator


nlp = Nlp.for_language(Languages.DE)
default_doc = nlp('Wenn Alice eine Anfrage macht')
django_project = DjangoProject('django_sample_project.apps.config.settings')


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
    mocker.patch('deep_translator.DeepL.translate', MockTranslator())
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
    mocker.patch('deep_translator.DeepL.translate', MockTranslator())
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
    mocker.patch('deep_translator.DeepL.translate', MockTranslator())
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
    mocker.patch('deep_translator.DeepL.translate', MockTranslator())
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
        (nlp('Dann sollte die Liste vier Einträge haben.'), 0.7, 1),
        (nlp('Dann sollte in der Antwort drei Aufträge enthalten sein'), 0.7, 1),
        (nlp('Dann sollte vier Einträge enthalten sein.'), 0.7, 1),
        (nlp('Dann sollte der Auftrag den Namen "Alice" haben.'), 0, 0.4),
        (nlp('Dann sollte die Antwort den Status 200 haben.'), 0, 0.4),
        (nlp('Dann sollte der Fehler "abc" enthalten.'), 0, 0.4),
    ]
)
def test_many_check_length_response_converter_compatibility(doc, min_compatibility, max_compatibility, mocker):
    """Check that the ManyLengthResponseConverter detects the compatibility of different documents correctly."""
    mocker.patch('deep_translator.DeepL.translate', MockTranslator())
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
    mocker.patch('deep_translator.DeepL.translate', MockTranslator())
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
    assert statements[0].expression.value_1.function_kwargs[0].variable_ref == converter.get_response_variable_reference()
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
    mocker.patch('deep_translator.DeepL.translate', MockTranslator())
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
    mocker.patch('deep_translator.DeepL.translate', MockTranslator())
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
    mocker.patch('deep_translator.DeepL.translate', MockTranslator())
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
    mocker.patch('deep_translator.DeepL.translate', MockTranslator())
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
    mocker.patch('deep_translator.DeepL.translate', MockTranslator())
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
    mocker.patch('deep_translator.DeepL.translate', MockTranslator())
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
    mocker.patch('deep_translator.DeepL.translate', MockTranslator())
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
