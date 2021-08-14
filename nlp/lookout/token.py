from abc import ABC

from django_meta.api import Methods
from nlp.generate.constants import CompareChar
from nlp.lookout.base import Lookout
from nlp.similarity import CosineSimilarity
from nlp.utils import NoToken, token_is_noun, token_is_verb
from nlp.vocab import FILE_EXTENSIONS


class TokenLookout(Lookout, ABC):
    similarity_benchmark = 0.8
    use_lemma_for_variation = True

    def __init__(self, document, locate_on_init=False):
        try:
            doc_language = document.lang_
        except AttributeError:
            doc_language = document[0].lang_

        self.document = document
        super().__init__(
            text=str(document),
            src_language=doc_language,
            locate_on_init=locate_on_init,
            scope_object=document,
        )

    @property
    def doc_src_language(self):
        return self.document

    def get_compare_variations(self, token, keyword):
        variations = []

        if self.use_lemma_for_variation:
            token = token.lemma_
        else:
            token = str(token)

        # and the translations for both languages
        translator_to_en = self.translator_to_en
        translator_to_doc = self.translator_to_src

        # get for both languages for both inputs the nlp doc
        token = self.nlp_src_language(token)
        token_en = self.nlp_en(translator_to_en.translate(str(token)))
        compare_value_en = self.nlp_en(keyword)
        compare_value_doc = self.nlp_src_language(translator_to_doc.translate(keyword))

        # get variations where both languages are compared
        variations.append((token, compare_value_doc))
        variations.append((token_en, compare_value_en))
        variations.append((token, compare_value_en))

        return variations

    def locate(self, raise_exception=False, **kwargs):
        return super().locate(document=self.document, raise_exception=raise_exception, **kwargs)

    def get_keywords(self, output_object):
        return []

    def get_similarity(self, value_1, value_2):
        """Get the similarity of the token. By default only Cosine is used."""
        return CosineSimilarity(value_1, value_2).get_similarity()

    def get_output_objects(self, document, *args, **kwargs):
        return [t for t in document]

    def get_output_object_fallback(self):
        return NoToken()

    @property
    def fittest_token(self):
        """Backwards compatibility and better understandable."""
        return self.fittest_output_object


class WordLookout(TokenLookout):
    def __init__(self, document, words, locate_on_init=False):
        super().__init__(document, locate_on_init=locate_on_init)
        self.words = words

    def get_keywords(self, token):
        return [self.words] if not isinstance(self.words, list) else self.words


class NounLookout(WordLookout):
    def output_object_is_relevant(self, token):
        return token_is_noun(token)


class VerbLookout(WordLookout):
    def output_object_is_relevant(self, token):
        return token_is_verb(token)


class FileLookout(NounLookout):
    """This lookout finds a token that indicates a file."""
    def __init__(self, document):
        super().__init__(document, 'file')


class FileExtensionLookout(TokenLookout):
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
            variations = super().get_compare_variations(part, file_description)
            similarity_fn = super().get_similarity

            return max([similarity_fn(token_var, desc_var) for token_var, desc_var in variations])

        return 0

    def output_object_is_relevant(self, token):
        """Files that are named entities, proper nouns or nouns may describe the extension."""
        return token.pos_ == 'PROPN' or any([token in ent for ent in list(token.doc.ents)]) or token.pos_ == 'NOUN'

    def get_keywords(self, token):
        """Get the extension and description values from the dict."""
        # common file extensions
        return [(key, value) for key, value in FILE_EXTENSIONS.items()]

    @property
    def fittest_keyword(self):
        """Since we always use the tuples, get the extension from that tuple"""
        default = super().fittest_keyword
        return default[0] if default else None

    def get_compare_variations(self, token, keyword):
        """Simplify the variations because it would cause a lot of calculations."""
        return [(token, keyword)]


class ComparisonLookout(TokenLookout):
    """
    This lookout can be used to search for comparisons (similar to ==, <= etc.).
    """
    use_lemma_for_variation = False

    GREATER_KEYWORDS = ['more', 'greater']
    SMALLER_KEYWORDS = ['less', 'fewer', 'smaller']

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

        self.or_lookout = WordLookout(self.document, 'or')
        self.or_lookout.locate()

    def _get_comparison(self):
        """
        Returns the _comparison char for the given document.
        """
        # if there is an or, it is expected to be fine to be equal too
        has_or = bool(self.or_lookout.fittest_output_object)

        if self.fittest_keyword in self.GREATER_KEYWORDS:
            if has_or:
                return CompareChar.GREATER_EQUAL

            return CompareChar.GREATER

        if self.fittest_keyword in self.SMALLER_KEYWORDS:
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

    def get_keywords(self, output_object):
        """Return values that indicate greater or smaller."""
        return self.GREATER_KEYWORDS + self.SMALLER_KEYWORDS

    def output_object_is_relevant(self, token):
        """More, less etc. determiners. So skip everything else."""
        return token.pos_ == 'DET'


class RestActionLookout(TokenLookout):
    """This lookout finds a token that indicates a special REST action."""
    GET_KEYWORDS = ['detail', 'list', 'get', 'fetch']
    DELETE_KEYWORDS = ['remove', 'delete', 'clear', 'destroy']
    UPDATE_KEYWORDS = ['change', 'update', 'modify', 'adjust']
    CREATE_KEYWORDS = ['create', 'generate', 'add']

    @property
    def method(self):
        if self.fittest_keyword in self.GET_KEYWORDS:
            return Methods.GET

        if self.fittest_keyword in self.DELETE_KEYWORDS:
            return Methods.DELETE

        if self.fittest_keyword in self.UPDATE_KEYWORDS:
            return Methods.PUT

        if self.fittest_keyword in self.CREATE_KEYWORDS:
            return Methods.POST

        return None

    def output_object_is_relevant(self, token):
        """Only verbs and nouns are used to check which action is meant."""
        return token_is_verb(token) or token_is_noun(token)

    def get_keywords(self, token):
        """Get words that can indicate a REST action."""
        return self.GET_KEYWORDS + self.DELETE_KEYWORDS + self.CREATE_KEYWORDS + self.UPDATE_KEYWORDS

