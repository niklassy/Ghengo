from core.constants import Languages
from django_meta.api import Methods
from nlp.generate.constants import CompareChar
from nlp.setup import Nlp
from nlp.similarity import CosineSimilarity
from nlp.translator import CacheTranslator
from nlp.utils import NoToken, token_is_verb, token_is_noun
from nlp.vocab import FILE_EXTENSIONS


class Locator(object):
    """
    Is responsible for locate tokens in a document given criteria.
    """
    SIMILARITY_BENCHMARK = 0.8
    use_lemma_for_variation = True

    def __init__(self, document):
        self.document = document
        try:
            self.doc_language = self.document.lang_
        except AttributeError:
            self.doc_language = document[0].lang_

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

    def _get_best_compare_value(self, value):
        return value

    def locate(self):
        """Locate a token that fits the compare values best."""
        if self._fittest_token is not None:
            return

        for token in self.document:
            if self._highest_similarity >= 1:
                break

            if not self.token_is_relevant(token):
                continue

            for compare_value in self.get_compare_values():
                for token_variety, compare_value_variety in self.get_variations(token, compare_value):
                    similarity = self.get_similarity(token_variety, compare_value_variety)

                    if similarity > self._highest_similarity:
                        self._fittest_token = token
                        self._highest_similarity = similarity
                        self._best_compare_value = self._get_best_compare_value(compare_value)

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

        if self.use_lemma_for_variation:
            token = token.lemma_
        else:
            token = str(token)

        # get the nlp
        nlp_en = Nlp.for_language(Languages.EN)
        nlp_doc = Nlp.for_language(self.doc_language)

        # and the translations for both languages
        translator_to_en = CacheTranslator(src_language=self.doc_language, target_language=Languages.EN)
        translator_to_doc = CacheTranslator(src_language=Languages.EN, target_language=self.doc_language)

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


class FileExtensionLocator(Locator):
    use_lemma_for_variation = False

    def get_similarity(self, token, compare_value):
        """Compare value is a tuple here, so compare both values"""
        file_extension = compare_value[0]
        file_description = compare_value[1]

        token_str = str(token)
        token_parts = token_str.split('-')

        for part in token_parts:
            if file_extension == part.lower():
                return 1

            # try to find a token where the description may fit
            variations = super().get_variations(part, file_description)
            similarity_fn = super().get_similarity

            return max([similarity_fn(token_var, desc_var) for token_var, desc_var in variations])

        return 0

    def token_is_relevant(self, token):
        """Files that are named entities, proper nouns or nouns may describe the extension."""
        return token.pos_ == 'PROPN' or any([token in ent for ent in list(token.doc.ents)]) or token.pos_ == 'NOUN'

    def get_compare_values(self):
        """Get the extension and description values from the dict."""
        # common file extensions
        return [(key, value) for key, value in FILE_EXTENSIONS.items()]

    def _get_best_compare_value(self, value):
        """Since we always use the tuples, get the extension from that tuple"""
        return value[0]

    def get_variations(self, token, compare_value):
        """Simplify the variations because it would cause a lot of calculations."""
        return [(token, compare_value)]


class WordLocator(Locator):
    """
    This is a locator to search for a given word.
    """
    def __init__(self, document, word):
        super().__init__(document)
        self.word = word

    def get_compare_values(self):
        return [self.word]


class NounLocator(WordLocator):
    def token_is_relevant(self, token):
        return token_is_noun(token)


class FileLocator(NounLocator):
    """This locator finds a token that indicates a file."""
    def __init__(self, document):
        super().__init__(document, 'file')


class ComparisonLocator(Locator):
    """
    This locator can be used to search for comparisons (similar to ==, <= etc.).
    """
    use_lemma_for_variation = False

    GREATER_VALUES = ['more', 'greater']
    SMALLER_VALUES = ['less', 'fewer', 'smaller']

    REVERSE_CHARS = {
        CompareChar.EQUAL: CompareChar.EQUAL,
        CompareChar.SMALLER: CompareChar.GREATER,
        CompareChar.SMALLER_EQUAL: CompareChar.GREATER_EQUAL,
        CompareChar.GREATER: CompareChar.SMALLER,
        CompareChar.GREATER_EQUAL: CompareChar.SMALLER_EQUAL,
    }

    def __init__(self, document, reverse=False):
        """
        You can pass reverse to reverse the _comparison value. This can be useful in cases where the code output
        is not in the order of the text.
        """
        super().__init__(document)
        self.reverse = reverse

        self.or_locator = WordLocator(self.document, 'or')
        self.or_locator.locate()

    def _get_comparison(self):
        """
        Returns the _comparison char for the given document.
        """
        # if there is an or, it is expected to be fine to be equal too
        has_or = bool(self.or_locator.fittest_token)

        if self._best_compare_value in self.GREATER_VALUES:
            if has_or:
                return CompareChar.GREATER_EQUAL

            return CompareChar.GREATER

        if self._best_compare_value in self.SMALLER_VALUES:
            if has_or:
                return CompareChar.SMALLER_EQUAL

            return CompareChar.SMALLER

        return CompareChar.EQUAL

    @property
    def _comparison(self):
        """
        Returns the compare char.
        """
        compare_value = self._get_comparison()
        if self.reverse:
            return self.REVERSE_CHARS[compare_value]

        return compare_value

    def get_comparison_for_value(self, python_value):
        """
        Returns the determined _comparison for a given python value.
        """
        self.locate()

        if python_value is None or isinstance(python_value, bool):
            return CompareChar.IS

        return self._comparison

    def get_compare_values(self):
        """Return values that indicate greater or smaller."""
        return self.GREATER_VALUES + self.SMALLER_VALUES

    def token_is_relevant(self, token):
        """More, less etc. determiners. So skip everything else."""
        return token.pos_ == 'DET'


class RestActionLocator(Locator):
    """This locator finds a token that indicates a special REST action."""
    GET_VALUES = ['detail', 'list', 'get', 'fetch']
    DELETE_VALUES = ['remove', 'delete', 'clear', 'destroy']
    UPDATE_VALUES = ['change', 'update', 'modify', 'adjust']
    CREATE_VALUES = ['create', 'generate', 'add']

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

