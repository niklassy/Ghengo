import pytest

from core.constants import Languages
from django_meta.api import Methods
from nlp.generate.constants import CompareChar
from nlp.lookout.token import TokenLookout, FileExtensionLookout, WordLookout, ComparisonLookout, RestActionLookout
from nlp.setup import Nlp
from nlp.tests.utils import MockTranslator
from nlp.utils import NoToken

nlp = Nlp.for_language(Languages.DE)


def test_lookout_fittest_token(mocker):
    """Check that the fittest token is only determined when locate is called."""
    mocker.patch('deep_translator.DeepL.translate', MockTranslator())
    lookout = TokenLookout(nlp('Sie spielt mit drei Bällen.'))
    assert lookout.fittest_output_object is None
    lookout.locate()
    assert lookout.fittest_output_object is not None
    assert isinstance(lookout.fittest_output_object, NoToken)


def test_lookout_get_variations(mocker):
    """Check that the fittest token is only determined when locate is called."""
    mocker.patch('deep_translator.DeepL.translate', MockTranslator())
    lookout = TokenLookout(nlp('Sie spielt mit drei Bällen.'))
    variations = lookout.get_compare_variations(nlp('Auftrag')[0], 'User')
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
def test_file_extension_lookout(doc, token_index, output, mocker):
    """Check that the file extension lookout works as expected."""
    mocker.patch('deep_translator.DeepL.translate', MockTranslator())
    lookout = FileExtensionLookout(doc)
    lookout.locate()
    assert lookout.fittest_output_object == doc[token_index]
    assert lookout.fittest_keyword == output


@pytest.mark.parametrize(
    'word, doc, token_index', [
        ('file', nlp('Sie erstellt eine Photoshop-Datei'), 3),
        ('time', nlp('Es ist nur eine Frage der Zeit'), 6),
        ('or', nlp('Er oder sie'), 1),
        ('order', nlp('Ein Auftrag ist reingekommen'), 1),
    ]
)
def test_word_lookout(word, doc, token_index, mocker):
    """Checks if the word lookout works as expected."""
    mocker.patch('deep_translator.DeepL.translate', MockTranslator())
    lookout = WordLookout(doc, word)
    lookout.locate()
    assert lookout.fittest_output_object == doc[token_index]
    assert lookout.fittest_keyword == word


@pytest.mark.parametrize(
    'doc, token_index, output', [
        (nlp('Es sind weniger als drei Spieler'), 2, CompareChar.SMALLER),
        (nlp('Wir brauchen zwei oder weniger Träger'), 4, CompareChar.SMALLER_EQUAL),
        (nlp('Wir brauchen zwei oder mehr Träger'), 4, CompareChar.GREATER_EQUAL),
        (nlp('Wir brauchen mehr als sieben Träger'), 2, CompareChar.GREATER),
        (nlp('Es sollten zehn Ausgaben sein.'), None, CompareChar.EQUAL),
    ]
)
def test_word_lookout(doc, token_index, output, mocker):
    """Checks if the Comparisonlookout works as expected."""
    mocker.patch('deep_translator.DeepL.translate', MockTranslator())
    lookout = ComparisonLookout(doc)
    lookout.locate()
    assert lookout._comparison == output

    if token_index is not None:
        assert lookout.fittest_output_object == doc[token_index]
    else:
        assert isinstance(lookout.fittest_output_object, NoToken)


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
def test_word_lookout(doc, token_index, output, mocker):
    """Checks if the RestActionlookout works as expected."""
    mocker.patch('deep_translator.DeepL.translate', MockTranslator())
    lookout = RestActionLookout(doc)
    lookout.locate()
    assert lookout.method == output

    if token_index is not None:
        assert lookout.fittest_output_object == doc[token_index]
    else:
        assert isinstance(lookout.fittest_output_object, NoToken)
