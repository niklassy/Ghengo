import pytest

from core.constants import Languages
from django_meta.model import AbstractModelFieldWrapper, AbstractModelWrapper
from nlp.extractor.base import Extractor, ManyExtractor
from nlp.generate.pytest.suite import PyTestTestSuite
from nlp.setup import Nlp

suite = PyTestTestSuite('bar')
default_test_case = suite.create_and_add_test_case('foo')
model_wrapper = AbstractModelWrapper('Order')
field = AbstractModelFieldWrapper('name')
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
def test_extract_python_value(value, expected_value):
    """Check that the default extract value returns python values depending on the input."""
    extractor = Extractor(default_test_case, '', value, document)
    assert extractor.extract_value() == expected_value
    assert type(extractor.extract_value()) == type(expected_value)


def test_output_instance():
    """Check if the output instance is set correctly and the data is passed."""
    extractor = Extractor(default_test_case, '', '1', document)
    output_instance = extractor.output
    assert isinstance(output_instance, extractor.output_class)
    assert output_instance.document == document
    assert output_instance.source == '1'


@pytest.mark.parametrize(
    'doc, token_index, expected_output', [
        (nlp('Wenn sie einen Auftrag mit den Sammlungen 1, 2 und 3 erstellt'), 6, [1, 2, 3]),
        (nlp('Wenn sie einen Auftrag mit den Sammlungen Alice und Bob erstellt'), 6, ['Alice', 'Bob']),
        (nlp('Wenn sie einen Auftrag mit den Sammlungen "{\'1\': 1}" erstellt'), 6, [{'1': 1}]),
    ]
)
def test_many_extractor_mixin(doc, token_index, expected_output):
    """Check that many values are correctly handled."""
    extractor = ManyExtractor(default_test_case, '', doc[token_index], doc)
    assert extractor.extract_value() == expected_output
