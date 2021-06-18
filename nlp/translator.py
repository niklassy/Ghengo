import json
from pathlib import Path

from deep_translator import GoogleTranslator


class CacheTranslator(object):
    cache = {}

    def __init__(self, src_language, target_language):
        # dont reset cache here, since we want to keep it on class level
        self.src_language = src_language
        self.target_language = target_language

        if self.should_translate:
            self.translator = GoogleTranslator(source=src_language, target=target_language)
        else:
            self.translator = None

    @property
    def cache_path(self):
        directory_path = Path(__file__).parent.absolute()
        return '{}/translation_cache/{}_to_{}.json'.format(directory_path, self.src_language, self.target_language)

    def create_cache(self):
        with open(self.cache_path, 'w') as file:
            file.write('{}')
            file.close()

    def write_to_cache(self, text, translation):
        file_content = self.get_cache()

        with open(self.cache_path, 'w') as file:
            file_content[self.get_cache_name_for_text(text)] = translation
            file.write(json.dumps(file_content, indent=2, sort_keys=True))
            file.close()

    def read_from_cache(self, text):
        content = self.get_cache()
        return content[text]

    def get_cache(self):
        try:
            with open(self.cache_path) as file:
                return json.load(file)
        except FileNotFoundError:
            self.create_cache()
            return self.get_cache()

    @property
    def should_translate(self):
        return self.src_language != self.target_language

    @classmethod
    def get_cache_name_for_text(cls, text):
        return text

    def translate(self, text, **kwargs):
        if not self.should_translate:
            return text

        cache_index = self.get_cache_name_for_text(text)
        if cache_index in self.get_cache():
            return self.read_from_cache(cache_index)

        translation = self.translator.translate(text, **kwargs)
        self.write_to_cache(text, translation)
        return translation
