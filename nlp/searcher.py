import inspect

from django.contrib.auth.models import Permission

from core.constants import Languages
from django_meta.api import UrlPatternAdapter, Methods, AbstractApiFieldAdapter, ApiFieldAdapter
from django_meta.model import AbstractModelFieldAdapter, AbstractModelAdapter
from nlp.locator import RestActionLocator
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
            self._translator_to_en = CacheTranslator(src_language=self.src_language, target_language=Languages.EN)
        return self._translator_to_en

    @property
    def translator_to_src(self):
        if self._translator_to_src is None:
            self._translator_to_src = CacheTranslator(src_language=Languages.EN, target_language=self.src_language)
        return self._translator_to_src

    @property
    def nlp_en(self):
        return Nlp.for_language(Languages.EN)

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

            # use the basic version if only one word is passed
            doc_input = self.doc_src_language
            if len(self.doc_src_language) == 1:
                doc_input = Nlp.for_language(self.src_language)(self.doc_src_language[0].lemma_)

            # create documents for english and source language to get the similarity
            # en - keyword
            comparisons.append((self.doc_en, self.nlp_en(keyword)))
            # src - keyword
            comparisons.append((doc_input, self.nlp_src_language(keyword)))
            # src - keyword translated to src
            comparisons.append((doc_input, self.nlp_src_language(translated_keyword)))

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


class ClassArgumentSearcher(Searcher):
    """
    This searcher searches tokens that could represent the argument/ parameter of an __init__ of a given class.
    """
    def get_keywords(self, parameter_name):
        return [parameter_name]

    def get_possible_results(self, cls, exclude_parameters=None, *args, **kwargs):
        signature = inspect.signature(cls.__init__)
        parameters = dict(signature.parameters)

        # remove self as it is not passed to init from outside
        del parameters['self']
        if exclude_parameters is None:
            exclude_parameters = []

        # remove any parameters that are marked as excluded
        for exclude_parameter in exclude_parameters:
            try:
                del parameters[exclude_parameter]
            except KeyError:
                pass

        # only use the names for now
        return [param.name for param in parameters.values()]


class ModelFieldSearcher(Searcher):
    def get_convert_fallback(self):
        return AbstractModelFieldAdapter(name=self.translator_to_en.translate(self.text))

    def get_keywords(self, field):
        return [field.name, getattr(field, 'verbose_name', None)]

    def get_possible_results(self, model_adapter, **kwargs):
        return model_adapter.fields


class SerializerFieldSearcher(Searcher):
    def get_convert_fallback(self):
        return AbstractApiFieldAdapter(name=self.translator_to_en.translate(self.text))

    def get_keywords(self, field):
        return [field.source]

    def get_possible_results(self, serializer, **kwargs):
        if not serializer:
            return []

        return [ApiFieldAdapter(api_field=field) for field in serializer.fields.fields.values()]


class ModelSearcher(Searcher):
    def get_convert_fallback(self):
        return AbstractModelAdapter(name=self.translator_to_en.translate(self.text))

    def get_keywords(self, model):
        return [model.name, model.verbose_name]

    def get_possible_results(self, project_adapter, **kwargs):
        return project_adapter.get_models(as_adapter=True, include_django=True)


class PermissionSearcher(Searcher):
    """Can search for specific permissions in Django."""

    def get_convert_fallback(self):
        return None

    def get_keywords(self, permission):
        return [permission.codename, permission.name]

    def get_possible_results(self, *args, **kwargs):
        return Permission.objects.all()


class UrlSearcher(Searcher):
    def __init__(self, text, language, model_adapter, valid_methods):
        super().__init__(text, language)
        self.model_adapter = model_adapter

        if Methods.PUT in valid_methods:
            valid_methods = valid_methods.copy()
            valid_methods.append(Methods.PATCH)

        self.valid_methods = valid_methods

    def get_convert_fallback(self):
        return None

    def get_keywords(self, url_pattern):
        keywords = [url_pattern.url_name, url_pattern.reverse_name]

        if Methods.GET in url_pattern.methods:
            keywords += RestActionLocator.GET_VALUES

        if Methods.POST in url_pattern.methods:
            keywords += RestActionLocator.CREATE_VALUES

        if Methods.POST in url_pattern.methods or Methods.PATCH in url_pattern.methods:
            keywords += RestActionLocator.UPDATE_VALUES

        if Methods.DELETE in url_pattern.methods:
            keywords += RestActionLocator.DELETE_VALUES

        return keywords

    def get_possible_results(self, django_project, *args, **kwargs):
        url_patterns = django_project.list_urls(as_pattern=True)
        results = []

        for pattern in url_patterns:
            adapter = UrlPatternAdapter(pattern)

            if adapter.view_set is not None:
                # if the url does not have a valid method, skip it
                if not any([m in self.valid_methods for m in adapter.methods]):
                    continue

                # if the model is not the same, skip it
                if adapter.model_adapter.model != self.model_adapter.model:
                    continue

                results.append(adapter)

        return results
