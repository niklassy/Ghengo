import inspect
import json
import os
from json import JSONDecodeError
from pathlib import Path

from deep_translator import DeepL

from settings import Settings


class CacheTranslator(object):
    """
    This translator uses the GoogleTranslator but saves the results in a file. If the same
    text is used again later, it uses the cache instead of Google.
    """
    cache = {}

    def __init__(self, src_language, target_language):
        # dont reset cache here, since we want to keep it on class level
        self.src_language = src_language
        self.target_language = target_language

        api_key = Settings.DEEPL_API_KEY
        if self.src_language != self.target_language and api_key:
            # use deepl for translation
            self.translator = DeepL(
                source=src_language,
                target=target_language,
                api_key=api_key,
                use_free_api=Settings.DEEPL_USE_FREE_API
            )
        else:
            self.translator = None

    @property
    def cache_path(self):
        """Returns the path to the file where the cache can be found."""
        directory_path = Path(__file__).parent.absolute()
        return '{}/translation_cache/{}_to_{}.json'.format(directory_path, self.src_language, self.target_language)

    def create_cache(self):
        """
        Creates the file for the cache.
        """
        if self.translator is None:
            return

        with open(self.cache_path, 'w') as file:
            file.write('{}')
            file.close()

    def write_to_cache(self, text, translation):
        """
        Writes a text and its translation into the cache.
        """
        if self.translator is None:
            return

        file_content = self.get_cache()

        with open(self.cache_path, 'w') as file:
            file_content[self.get_cache_name_for_text(text)] = translation
            file.write(json.dumps(file_content, indent=2, sort_keys=True))
            file.close()

    def remove_from_cache(self, text):
        """Removes an entry from the cache."""
        if self.translator is None:
            return

        file_content = self.get_cache()

        with open(self.cache_path, 'w') as file:
            del file_content[self.get_cache_name_for_text(text)]
            file.write(json.dumps(file_content, indent=2, sort_keys=True))
            file.close()

    def delete_cache(self):
        """Deletes the whole cache for this translator."""
        self.create_cache()

    def read_from_cache(self, text):
        """
        Reads from the cache.
        """
        if not self.translator:
            return None

        content = self.get_cache()
        return content[text]

    def get_cache(self):
        """
        Returns the whole cache.
        """
        if not self.translator:
            return {}

        try:
            with open(self.cache_path) as file:
                content = json.load(file)
                file.close()
            return content
        except (FileNotFoundError, JSONDecodeError):
            self.create_cache()
            return self.get_cache()

    def translator_request_necessary(self, text):
        """Checks if it is necessary to call the translator for the given text."""
        cache_index = self.get_cache_name_for_text(text)
        return self.translator and cache_index not in self.get_cache()

    @classmethod
    def get_cache_name_for_text(cls, text):
        """Returns the index in the cache for a given text."""
        return text

    def _call_translator_safe(self, text, **kwargs):
        """
        This is a wrapper around the translator call. It is used to prevent calling any api while running tests.
        """
        # normally this is bad practice because the code considers cases where tests are run; I just wanna be safe
        # here and not call the Google api every time the tests run
        if os.environ.get('RUNNING_TESTS') == 'True':
            assert not inspect.isfunction(self.translator.translate), 'Remember to replace the translator in ' \
                                                                      'with mocker class with a __call__ to avoid ' \
                                                                      'unnecessary api calls while testing!! You need' \
                                                                      ' to add the following: \n\n ' \
                                                                      '"{}" for {} -> {}'.format(
                                                                            text,
                                                                            self.src_language,
                                                                            self.target_language
                                                                      )

        return self.translator.translate(text, **kwargs)

    def translate(self, text, **kwargs):
        """
        Translates a given text.
        """
        if all([char in '!"#$%&\'()*+,-./:;<=>?@[]^_`{|}~\\1234567890' for char in text]):
            return text

        if self.translator is None:
            translation = text
        elif self.translator_request_necessary(text):
            translation = self._call_translator_safe(text, **kwargs)
            self.write_to_cache(text, translation)
        else:
            translation = self.read_from_cache(text)

        return translation
