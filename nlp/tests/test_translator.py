from nlp.translator import CacheTranslator
from pytest_mock import MockerFixture


class CallCounter:
    def __init__(self, func):
        self.func = func
        self.call_counter = 0

    def __call__(self, *args, **kwargs):
        self.call_counter += 1
        return self.func(*args, **kwargs)


def test_cache_translator_should_translate_false(mocker: MockerFixture):
    """Check if the translator_to_en does not call translate when should_translate is False."""
    translator = CacheTranslator('de', 'de')
    assert translator.should_translate is False
    custom_translator = CallCounter(lambda a: a)
    assert custom_translator.call_counter == 0

    mocker.patch('deep_translator.GoogleTranslator.translate', custom_translator)
    assert translator.translate('Mein Text') == 'Mein Text'
    assert custom_translator.call_counter == 0


def test_cache_translator_should_translate_true(mocker: MockerFixture):
    """Check if the translator does call translate when should_translate is True."""
    translator = CacheTranslator('de', 'en')
    custom_translator = CallCounter(lambda a: a)
    assert custom_translator.call_counter == 0
    assert translator.should_translate is True

    mocker.patch('deep_translator.GoogleTranslator.translate', custom_translator)
    assert translator.translate('Mein Text') == 'Mein Text'
    assert custom_translator.call_counter == 1


def test_cache_translator_cached(mocker: MockerFixture):
    """Check if values that are used, are cached in all the translators."""
    translator = CacheTranslator('de', 'en')
    custom_translator = CallCounter(lambda a: a)
    mocker.patch('deep_translator.GoogleTranslator.translate', custom_translator)

    assert translator.translate('Mein Text') == 'Mein Text'
    assert custom_translator.call_counter == 1
    assert translator.cache['de__Mein Text'] == 'Mein Text'
    assert translator.translate('Mein Text') == 'Mein Text'
    assert custom_translator.call_counter == 1
