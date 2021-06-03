import nltk
import spacy

# nlp_en = spacy.load("en_core_web_trf")
# nlp_de = spacy.load("de_dep_news_trf")

# nltk.download('popular')
def setup_nlp():
    # nltk.download('punkt')
    # nltk.download('words')
    # nltk.download('wordnet')
    # nltk.download('maxent_ne_chunker')
    # nltk.download('averaged_perceptron_tagger')
    # andere Alternative: de_dep_news_trf en_core_web_trf
    return spacy.load("en_core_web_lg"), spacy.load("de_core_news_lg")


class _Nlp(object):
    def __init__(self):
        self._de_nlp = None
        self._en_nlp = None

    @property
    def de_nlp(self):
        if self._de_nlp is None:
            print('Setting up german nlp...')
            self._de_nlp = spacy.load('de_core_news_lg')
            print('German nlp done!')
        return self._de_nlp

    @property
    def en_nlp(self):
        if self._en_nlp is None:
            print('Setting up english nlp...')
            self._en_nlp = spacy.load('en_core_web_lg')
            print('English nlp done!')
        return self._en_nlp

    def for_language(self, language):
        if language == 'de':
            return self.de_nlp

        if language == 'en':
            return self.en_nlp

        raise ValueError('Language is not supported yet.')


Nlp = _Nlp()


def get_nlp_for_language(lang):
    if lang == 'de':
        return spacy.load('de_core_news_lg')

    return spacy.load('en_core_web_lg')

