from django_meta.project import AbstractModelInterface
from generate.utils import to_function_name
from nlp.clause import ClausedSentence
from nlp.settings import SIMILARITY_BENCHMARK
from nlp.setup import Nlp
from nlp.translator import CacheTranslator
from nlp.utils import get_non_stop_tokens, get_noun_chunks, get_named_entities, are_synonyms


class NoConversionFound(Exception):
    pass


class TextConverter(object):
    def __init__(self, text, src_language):
        self.text = text
        self.src_language = src_language
        self._translator = None
        self._doc_src_language = None
        self._doc_en = None

    @property
    def translator(self):
        if self._translator is None:
            self._translator = CacheTranslator(src_language=self.src_language, target_language='en')
        return self._translator

    @property
    def nlp_en(self):
        return Nlp.for_language('en')

    @property
    def nlp_src_language(self):
        return Nlp.for_language(self.src_language)

    @property
    def doc_src_language(self):
        if self._doc_src_language is None:
            self._doc_src_language = self.nlp_src_language(self.text)
        return self._doc_src_language

    @property
    def doc_en(self):
        if self._doc_en is None:
            self._doc_en = self.nlp_en(self.translator.translate(self.text))
        return self._doc_en

    def get_possible_conversions(self, *args, **kwargs):
        return []

    def get_comparisons(self, conversion):
        return []

    def get_similarity(self, input_doc, target_doc):
        if not input_doc.vector_norm or not target_doc.vector_norm:
            return 0

        # Return Cosine similarity
        # TODO: implement levenshtein similarity (for typos)?
        return input_doc.similarity(target_doc)

    def get_convert_fallback(self):
        return self.text

    def convert(self, *args, **kwargs):
        highest_similarity = 0
        fittest_conversion = None

        for conversion in self.get_possible_conversions(*args, **kwargs):
            comparisons = self.get_comparisons(conversion)

            for input_doc, target_doc in comparisons:
                similarity = self.get_similarity(input_doc, target_doc)

                if similarity > highest_similarity:
                    fittest_conversion = conversion
                    highest_similarity = similarity

        if highest_similarity <= SIMILARITY_BENCHMARK or fittest_conversion is None:
            return self.get_convert_fallback()

        return fittest_conversion


class TextToModelFieldConverter(TextConverter):
    def get_convert_fallback(self):
        class Fallback:
            name = to_function_name(self.text)
        return Fallback()

    def get_comparisons(self, field):
        verbose_name = getattr(field, 'verbose_name', None)
        field_name = field.name

        comparisons = [
            (self.doc_en, self.nlp_en(field_name.replace('_', ' '))),
            (self.doc_src_language, self.nlp_src_language(field_name.replace('_', ' '))),
        ]

        if bool(verbose_name):
            comparisons.append((self.doc_en, self.nlp_en(verbose_name.replace('_', ' '))))
            comparisons.append((self.doc_src_language, self.nlp_src_language(verbose_name.replace('_', ' '))))

        return comparisons

    def get_possible_conversions(self, *args, **kwargs):
        return kwargs['model_interface'].fields


class TextToModelConverter(TextConverter):
    def get_convert_fallback(self):
        return AbstractModelInterface(name=self.text)

    def get_comparisons(self, model):
        verbose_name = model.verbose_name
        name = model.name

        comparisons = [
            (self.doc_en, self.nlp_en(name)),
            (self.doc_src_language, self.nlp_src_language(name)),
        ]

        if bool(verbose_name):
            comparisons.append((self.doc_en, self.nlp_en(verbose_name)))
            comparisons.append((self.doc_src_language, self.nlp_src_language(verbose_name)))

        return comparisons

    def get_possible_conversions(self, *args, **kwargs):
        return kwargs['project_interface'].get_models(as_interface=True, include_django=True)
