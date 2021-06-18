from pytest_mock import MockerFixture

from nlp.translator import CacheTranslator


class CallCounter:
    def __init__(self, func):
        self.func = func
        self.call_counter = 0

    def __call__(self, *args, **kwargs):
        self.call_counter += 1
        return self.func(*args, **kwargs)


def test_translator_get_cache():
    translator = CacheTranslator('es', 'en')
    assert translator.get_cache() == {}


def test_translator_delete_cache(mocker: MockerFixture):
    """Check if the deleting of the cache works as expected."""
    translator = CacheTranslator('es', 'en')
    custom_translator = CallCounter(lambda a: a)
    mocker.patch('deep_translator.GoogleTranslator.translate', custom_translator)
    translator.translate('______foo_______')
    assert translator.get_cache() == {'______foo_______': '______foo_______'}
    translator.delete_cache()
    assert translator.get_cache() == {}


def test_translator_translate_cache(mocker: MockerFixture):
    """Check if a value already exists in the cache, it is used instead of the one from the translator."""
    translator = CacheTranslator('es', 'en')
    custom_translator = CallCounter(lambda a: a)
    mocker.patch('deep_translator.GoogleTranslator.translate', custom_translator)
    assert translator.translate('______foo_______') == '______foo_______'
    assert custom_translator.call_counter == 1
    assert translator.get_cache() == {'______foo_______': '______foo_______'}
    translator.translate('______foo_______')
    assert custom_translator.call_counter == 1
    translator.write_to_cache('______foo_______', '12345')
    assert translator.translate('______foo_______') == '12345'
    translator.delete_cache()


def test_translator_request_necessary(mocker: MockerFixture):
    """Check if translator_request_necessary works as expected."""
    translator = CacheTranslator('es', 'en')
    custom_translator = CallCounter(lambda a: a)
    mocker.patch('deep_translator.GoogleTranslator.translate', custom_translator)
    translator.write_to_cache('foo', 'bar')
    assert translator.translator_request_necessary('foo') is False
    translator.remove_from_cache('foo')
    assert translator.translator_request_necessary('foo') is True
    translator.delete_cache()


def test_translator_same_language(mocker: MockerFixture):
    """Check if the translator does not work entirely when using the same language twice."""
    translator = CacheTranslator('es', 'es')
    custom_translator = CallCounter(lambda a: a)
    mocker.patch('deep_translator.GoogleTranslator.translate', custom_translator)
    assert translator.translate('text') == 'text'
    assert custom_translator.call_counter == 0
    translator.delete_cache()
