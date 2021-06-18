from django_meta.project import AbstractModelInterface, AbstractModelField
from nlp.setup import Nlp
from nlp.similarity import CosineSimilarity, ContainsSimilarity
from nlp.translator import CacheTranslator


class NoConversionFound(Exception):
    pass


class Searcher(object):
    SIMILARITY_BENCHMARK = 0.59

    def __init__(self, text, src_language):
        self.text = text
        self.src_language = src_language
        self._translator_to_en = None
        self._translator_to_src = None
        self._doc_src_language = None
        self._doc_en = None

    @property
    def translator_to_en(self):
        if self._translator_to_en is None:
            self._translator_to_en = CacheTranslator(src_language=self.src_language, target_language='en')
        return self._translator_to_en

    @property
    def translator_to_src(self):
        if self._translator_to_src is None:
            self._translator_to_src = CacheTranslator(src_language='en', target_language=self.src_language)
        return self._translator_to_src

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
            self._doc_en = self.nlp_en(self.translator_to_en.translate(self.text))
        return self._doc_en

    def get_possible_results(self, *args, **kwargs):
        """
        Returns all possible values that the text can transform to.
        """
        return []

    def get_comparisons(self, conversion_object):
        """
        Returns a list of 2-tuples [(a, b)] with values that will be compared for similarity.

        The values will be compared in all languages.

        Arguments:
            conversion_object: one object that was returned from `get_possible_results`
        """
        keywords = self.get_keywords(conversion_object)
        comparisons = []
        filtered_keywords = []

        for keyword in keywords:
            if not keyword or keyword.lower() in filtered_keywords:
                continue
            filtered_keywords.append(keyword)

        for keyword in filtered_keywords:
            if not keyword:
                continue

            translated_keyword = self.translator_to_src.translate(keyword.replace('_', ' '))

            # create documents for english and source language to get the similarity
            comparisons.append((self.doc_en, self.nlp_en(keyword.replace('_', ' '))))
            comparisons.append((self.doc_src_language, self.nlp_src_language(keyword.replace('_', ' '))))
            comparisons.append((self.doc_src_language, self.nlp_src_language(translated_keyword)))

        return comparisons

    def get_similarity(self, input_doc, target_doc):
        """Returns the similarity between two docs/ tokens in a range from 0 - 1."""
        # TODO: implement levenshtein similarity (for typos)?
        contains_similarity = ContainsSimilarity(input_doc, target_doc).get_similarity()
        cos_similarity = CosineSimilarity(input_doc, target_doc).get_similarity()

        total_similarity = contains_similarity + cos_similarity
        if total_similarity > 1:
            return 1
        return total_similarity

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

        for conversion in self.get_possible_results(*args, **kwargs):
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
        return AbstractModelField(name=self.translator_to_en.translate(self.text))

    def get_keywords(self, field):
        return [field.name, getattr(field, 'verbose_name', None)]

    def get_possible_results(self, model_interface):
        return model_interface.fields


class ModelSearcher(Searcher):
    def get_convert_fallback(self):
        return AbstractModelInterface(name=self.translator_to_en.translate(self.text))

    def get_keywords(self, model):
        return [model.name, model.verbose_name]

    def get_possible_results(self, project_interface):
        return project_interface.get_models(as_interface=True, include_django=True)
