from django_meta.project import AbstractModelInterface, AbstractModelField
from nlp.setup import Nlp
from nlp.similarity import CosineSimilarity
from nlp.translator import CacheTranslator


class NoConversionFound(Exception):
    pass


class Searcher(object):
    SIMILARITY_BENCHMARK = 0.59

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

    def get_comparisons(self, conversion_object):
        """
        Returns a list of 2-tuples [(a, b)] with values that will be compared for similarity.

        The values will be compared in all languages.

        Arguments:
            conversion_object: one object that was returned from `get_possible_conversions`
        """
        keywords = self.get_keywords(conversion_object)
        comparisons = []

        for keyword in keywords:
            if not keyword:
                continue

            # create documents for english and source language to get the similarity
            comparisons.append((self.doc_en, self.nlp_en(keyword.replace('_', ' '))))
            comparisons.append((self.doc_src_language, self.nlp_src_language(keyword.replace('_', ' '))))

        return comparisons

    def get_similarity(self, input_doc, target_doc):
        """Returns the similarity between two docs/ tokens in a range from 0 - 1."""
        # TODO: implement levenshtein similarity (for typos)?
        return CosineSimilarity(input_doc, target_doc).get_similarity()

    def get_keywords(self, conversion_object):
        """Returns all they keywords that this class should look for in the conversion object."""
        return []

    def get_convert_fallback(self):
        """Returns a fallback in case no match has been found."""
        return self.text

    def search(self, *args, raise_exception=False, **kwargs):
        """
        Search an object that represents the text that was given on init.  If none is found,
        this will either return a fallback (see `get_convert_fallback`) or raises an exception if `raise_exception`
        is true.
        """
        highest_similarity = 0
        fittest_conversion = None

        for conversion in self.get_possible_conversions(*args, **kwargs):
            comparisons = self.get_comparisons(conversion)

            for input_doc, target_doc in comparisons:
                similarity = self.get_similarity(input_doc, target_doc)

                if similarity > highest_similarity:
                    fittest_conversion = conversion
                    highest_similarity = similarity

        if highest_similarity <= self.SIMILARITY_BENCHMARK or fittest_conversion is None:
            if raise_exception:
                raise NoConversionFound()

            return self.get_convert_fallback()

        return fittest_conversion


class ModelFieldSearcher(Searcher):
    def get_convert_fallback(self):
        return AbstractModelField(name=self.translator.translate(self.text))

    def get_keywords(self, field):
        return [field.name, getattr(field, 'verbose_name', None)]

    def get_possible_conversions(self, model_interface):
        return model_interface.fields


class ModelSearcher(Searcher):
    def get_convert_fallback(self):
        return AbstractModelInterface(name=self.translator.translate(self.text))

    def get_keywords(self, model):
        return [model.name, model.verbose_name]

    def get_possible_conversions(self, project_interface):
        return project_interface.get_models(as_interface=True, include_django=True)
