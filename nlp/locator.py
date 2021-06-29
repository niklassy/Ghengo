from django_meta.api import Methods
from nlp.setup import Nlp
from nlp.similarity import CosineSimilarity
from nlp.translator import CacheTranslator
from nlp.utils import NoToken, token_is_verb, token_is_noun


class Locator(object):
    """
    Is responsible for locate tokens in a document given criteria.
    """
    SIMILARITY_BENCHMARK = 0.8

    def __init__(self, document):
        self.document = document
        self.doc_language = self.document.lang_
        self._fittest_token = None
        self._best_compare_value = None
        self._highest_similarity = 0

    def token_is_relevant(self, token):
        """Can be used to skip certain tokens to increase performance."""
        return True

    @property
    def fittest_token(self):
        return self._fittest_token

    @property
    def best_compare_value(self):
        return self._best_compare_value

    @property
    def highest_similarity(self):
        return self._highest_similarity

    def locate(self):
        """Locate a token that fits the compare values best."""
        if self._fittest_token is not None:
            return

        for token in self.document:
            if not self.token_is_relevant(token):
                continue

            for compare_value in self.get_compare_values():
                for token_variety, compare_value_variety in self.get_variations(token.lemma_, compare_value):
                    similarity = self.get_similarity(token_variety, compare_value_variety)

                    if similarity > self._highest_similarity:
                        self._fittest_token = token
                        self._highest_similarity = similarity
                        self._best_compare_value = compare_value

                        if similarity >= 1:
                            break

                if self._highest_similarity >= 1:
                    break

        if self._highest_similarity < self.SIMILARITY_BENCHMARK or self._fittest_token is None:
            self._fittest_token = NoToken()
            self._best_compare_value = None

    def get_variations(self, token, compare_value):
        """Get some variations of the token and the compare value to make it easier to locate the tokens."""
        variations = []

        # get the nlp
        nlp_en = Nlp.for_language('en')
        nlp_doc = Nlp.for_language(self.doc_language)

        # and the translations for both languages
        translator_to_en = CacheTranslator(src_language=self.doc_language, target_language='en')
        translator_to_doc = CacheTranslator(src_language='en', target_language=self.doc_language)

        # get for both languages for both inputs the nlp doc
        token = nlp_doc(token)
        token_en = nlp_en(translator_to_en.translate(str(token)))
        compare_value_en = nlp_en(compare_value)
        compare_value_doc = nlp_doc(translator_to_doc.translate(compare_value))

        # get variations where both languages are compared
        variations.append((token, compare_value_doc))
        variations.append((token_en, compare_value_en))
        variations.append((token, compare_value_en))

        return variations

    def get_similarity(self, token, compare_value):
        """Get the similarity of the token. By default only Cosine is used."""
        return CosineSimilarity(token, compare_value).get_similarity()

    def get_compare_values(self):
        """Get all the values that the tokens will be compared to."""
        return []


class RestActionLocator(Locator):
    """This locator finds a token that indicates a special REST action."""
    GET_VALUES = ['list', 'get', 'detail', 'fetch']
    DELETE_VALUES = ['remove', 'delete', 'clear', 'destroy']
    UPDATE_VALUES = ['change', 'update', 'modify']
    CREATE_VALUES = ['create', 'generate']

    @property
    def method(self):
        if self._best_compare_value in self.GET_VALUES:
            return Methods.GET

        if self._best_compare_value in self.DELETE_VALUES:
            return Methods.DELETE

        if self._best_compare_value in self.UPDATE_VALUES:
            return Methods.PUT

        if self._best_compare_value in self.CREATE_VALUES:
            return Methods.POST

        return None

    def token_is_relevant(self, token):
        """Only verbs and nouns are used to check which action is meant."""
        return token_is_verb(token) or token_is_noun(token)

    def get_compare_values(self):
        """Get words that can indicate a REST action."""
        return self.GET_VALUES + self.DELETE_VALUES + self.CREATE_VALUES + self.UPDATE_VALUES

