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

        self.reset_cache()

    def reset_cache(self):
        self.cache = {}

    @property
    def should_translate(self):
        return self.src_language != self.target_language

    def get_cache_name_for_text(self, text):
        return '{}__{}'.format(self.src_language, text)

    def translate(self, text, **kwargs):
        if not self.should_translate:
            return text

        cache_index = self.get_cache_name_for_text(text)
        if cache_index in self.cache:
            return self.cache[cache_index]

        translation = self.translator.translate(text, **kwargs)
        self.cache[cache_index] = translation
        return translation
