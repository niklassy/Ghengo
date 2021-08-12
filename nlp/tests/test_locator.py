import pytest

from core.constants import Languages
from django_meta.api import Methods
from nlp.generate.constants import CompareChar
from nlp.lookout.token import TokenLookout, FileExtensionLocator, WordLocator, ComparisonLocator, RestActionLocator
from nlp.setup import Nlp
from nlp.tests.utils import MockTranslator
from nlp.utils import NoToken

nlp = Nlp.for_language(Languages.DE)


def test_locator_fittest_token(mocker):
    """Check that the fittest token is only determined when locate is called."""
    mocker.patch('deep_translator.GoogleTranslator.translate', MockTranslator())
    locator = TokenLookout(nlp('Sie spielt mit drei Bällen.'))
    assert locator.fittest_output_object is None
    locator.locate()
    assert locator.fittest_output_object is not None
    assert isinstance(locator.fittest_output_object, NoToken)


def test_locator_get_variations(mocker):
    """Check that the fittest token is only determined when locate is called."""
    mocker.patch('deep_translator.GoogleTranslator.translate', MockTranslator())
    locator = TokenLookout(nlp('Sie spielt mit drei Bällen.'))
    variations = locator.get_compare_variations(nlp('Auftrag')[0], 'User')
    assert len(variations) == 3
    assert str(variations[0][0]) == 'Auftrag'
    assert str(variations[0][1]) == 'Benutzer'
    assert str(variations[1][0]) == 'order'
    assert str(variations[1][1]) == 'User'
    assert str(variations[2][0]) == 'Auftrag'
    assert str(variations[2][1]) == 'User'


@pytest.mark.parametrize(
    'doc, token_index, output', [
        (nlp('Sie erstellt eine Photoshop-Datei'), 3, 'psd'),
        (nlp('Sie erstellt eine Word-Datei'), 3, 'docx'),
        (nlp('Ich habe eine Text-Datei gefunden'), 3, 'txt'),
        (nlp('Peter erstellt ein Bild'), 3, 'png'),
        (nlp('Die CSV Datei ist ziemlich groß'), 1, 'csv'),
    ]
)
def test_file_extension_locator(doc, token_index, output, mocker):
    """Check that the file extension locator works as expected."""
    mocker.patch('deep_translator.GoogleTranslator.translate', MockTranslator())
    locator = FileExtensionLocator(doc)
    locator.locate()
    assert locator.fittest_output_object == doc[token_index]
    assert locator.fittest_keyword == output


@pytest.mark.parametrize(
    'word, doc, token_index', [
        ('file', nlp('Sie erstellt eine Photoshop-Datei'), 3),
        ('time', nlp('Es ist nur eine Frage der Zeit'), 6),
        ('or', nlp('Er oder sie'), 1),
        ('order', nlp('Ein Auftrag ist reingekommen'), 1),
    ]
)
def test_word_locator(word, doc, token_index, mocker):
    """Checks if the word locator works as expected."""
    mocker.patch('deep_translator.GoogleTranslator.translate', MockTranslator())
    locator = WordLocator(doc, word)
    locator.locate()
    assert locator.fittest_output_object == doc[token_index]
    assert locator.fittest_keyword == word


@pytest.mark.parametrize(
    'doc, token_index, output', [
        (nlp('Es sind weniger als drei Spieler'), 2, CompareChar.SMALLER),
        (nlp('Wir brauchen zwei oder weniger Träger'), 4, CompareChar.SMALLER_EQUAL),
        (nlp('Wir brauchen zwei oder mehr Träger'), 4, CompareChar.GREATER_EQUAL),
        (nlp('Wir brauchen mehr als sieben Träger'), 2, CompareChar.GREATER),
        (nlp('Es sollten zehn Ausgaben sein.'), None, CompareChar.EQUAL),
    ]
)
def test_word_locator(doc, token_index, output, mocker):
    """Checks if the ComparisonLocator works as expected."""
    mocker.patch('deep_translator.GoogleTranslator.translate', MockTranslator())
    locator = ComparisonLocator(doc)
    locator.locate()
    assert locator._comparison == output

    if token_index is not None:
        assert locator.fittest_output_object == doc[token_index]
    else:
        assert isinstance(locator.fittest_output_object, NoToken)


@pytest.mark.parametrize(
    'doc, token_index, output', [
        (nlp('Wir erstellen zwei Aufträge'), 1, Methods.POST),
        (nlp('Wir ändern zwei Aufträge'), 1, Methods.PUT),
        (nlp('Wir löschen zwei Aufträge'), 1, Methods.DELETE),
        (nlp('Wir holen zwei Aufträge'), 1, Methods.GET),
        (nlp('Wir die Liste der Aufträge'), 2, Methods.GET),
        (nlp('Ich esse Äpfel'), None, None),
    ]
)
def test_word_locator(doc, token_index, output, mocker):
    """Checks if the RestActionLocator works as expected."""
    mocker.patch('deep_translator.GoogleTranslator.translate', MockTranslator())
    locator = RestActionLocator(doc)
    locator.locate()
    assert locator.method == output

    if token_index is not None:
        assert locator.fittest_output_object == doc[token_index]
    else:
        assert isinstance(locator.fittest_output_object, NoToken)
