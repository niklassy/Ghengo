from django.contrib.auth.models import Permission

from django_meta.api import UrlPatternInterface, Methods
from django_meta.model import AbstractModelInterface, AbstractModelField
from nlp.setup import Nlp
from nlp.similarity import CosineSimilarity, ContainsSimilarity, LevenshteinSimilarity
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

        for keyword in set([k.replace('_', ' ') if k else None for k in keywords]):
            if not keyword or keyword in [str(key) for _, key in comparisons]:
                continue

            translated_keyword = self.translator_to_src.translate(keyword)

            # create documents for english and source language to get the similarity
            # en - keyword
            comparisons.append((self.doc_en, self.nlp_en(keyword)))
            # src - keyword
            comparisons.append((self.doc_src_language, self.nlp_src_language(keyword)))
            # src - keyword translated to src
            comparisons.append((self.doc_src_language, self.nlp_src_language(translated_keyword)))

        return comparisons

    def get_similarity(self, input_doc, target_doc):
        """Returns the similarity between two docs/ tokens in a range from 0 - 1."""
        cos_similarity = CosineSimilarity(input_doc, target_doc).get_similarity()

        # if cos is very sure, just use it
        if cos_similarity > 0.8:
            return cos_similarity

        cos_weight = 0.5
        levenshtein_weight = 0.3
        contains_weight = 0.2

        contains_similarity = ContainsSimilarity(input_doc, target_doc).get_similarity()
        levenshtein_similarity = LevenshteinSimilarity(input_doc, target_doc).get_similarity()
        total_similarity = (
            cos_similarity * cos_weight
        ) + (
            levenshtein_similarity * levenshtein_weight
        ) + (
            contains_similarity * contains_weight
        )

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


class PermissionSearcher(Searcher):
    """Can search for specific permissions in Django."""

    def get_convert_fallback(self):
        return None

    def get_keywords(self, permission):
        return [permission.codename, permission.name]

    def get_possible_results(self, *args, **kwargs):
        return Permission.objects.all()


class UrlSearcher(Searcher):
    def __init__(self, text, language, model_interface, valid_methods):
        super().__init__(text, language)
        self.model_interface = model_interface

        if Methods.PUT in valid_methods:
            valid_methods = valid_methods.copy()
            valid_methods.append(Methods.PATCH)

        self.valid_methods = valid_methods

    def get_convert_fallback(self):
        # TODO: maybe create a fallback??
        return None

    def get_keywords(self, url_pattern):
        keywords = [url_pattern.url_name, url_pattern.reverse_name]

        if Methods.GET in url_pattern.methods:
            keywords += ['get', 'list', '{} list'.format(self.model_interface.name)]

        if Methods.POST in url_pattern.methods:
            keywords.append('create')

        if Methods.POST in url_pattern.methods or Methods.PATCH in url_pattern.methods:
            keywords.append('update')

        if Methods.DELETE in url_pattern.methods:
            keywords.append('delete')

        return keywords

    def get_possible_results(self, django_project, *args, **kwargs):
        url_patterns = django_project.list_urls(as_pattern=True)
        results = []

        for pattern in url_patterns:
            interface = UrlPatternInterface(pattern)

            if interface.view_set is not None:
                # if the url does not have a valid method, skip it
                if not any([m in self.valid_methods for m in interface.methods]):
                    continue

                # if the model is not the same, skip it
                if interface.model_interface.model != self.model_interface.model:
                    continue

                results.append(interface)

        return results
