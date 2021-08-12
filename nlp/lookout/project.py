import inspect
from abc import ABC

from django.contrib.auth.models import Permission

from django_meta.api import AbstractApiFieldWrapper, ApiFieldWrapper, Methods, AbstractUrlPatternWrapper, \
    UrlPatternWrapper
from django_meta.model import AbstractModelFieldWrapper, AbstractModelWrapper
from nlp.lookout.base import Lookout
from nlp.lookout.token import RestActionLocator
from nlp.similarity import CosineSimilarity, ContainsSimilarity, LevenshteinSimilarity


class DjangoProjectLookout(Lookout, ABC):
    """
    This lookout is specialized to find stuff in Django projects.
    """
    similarity_benchmark = 0.59

    def prepare_keywords(self, keywords):
        return set([k.replace('_', ' ') if k else None for k in keywords])

    def search(self, *args, **kwargs):
        """For backwards compatibility..."""
        return self.locate(*args, **kwargs)

    def should_stop_looking_for_output(self):
        """Always look through all outputs"""
        return False

    def get_compare_variations(self, output_object, keyword):
        comparisons = []

        if not self.text or not keyword:
            return []

        translated_keyword = self.translator_to_src.translate(keyword)

        # use the basic version if only one word is passed
        doc_input = self.doc_src_language
        if len(self.doc_src_language) == 1:
            doc_input = self.nlp_src_language(self.doc_src_language[0].lemma_)

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
        contains_similarity = ContainsSimilarity(input_doc, target_doc).get_similarity()

        # if cos is very sure, just use it
        if cos_similarity > 0.8:
            return cos_similarity

        if contains_similarity == 1:
            return contains_similarity

        cos_weight = 0.5
        levenshtein_weight = 0.3
        contains_weight = 0.2

        levenshtein_similarity = LevenshteinSimilarity(input_doc, target_doc).get_similarity()
        total_similarity = (
            cos_similarity * cos_weight
        ) + (
            levenshtein_similarity * levenshtein_weight
        ) + (
            contains_similarity * contains_weight
        )

        return total_similarity


class ClassArgumentSearcher(DjangoProjectLookout):
    """
    This searcher searches tokens that could represent the argument/ parameter of an __init__ of a given class.
    """
    def get_output_object_fallback(self):
        return None

    def get_keywords(self, parameter_name):
        return [parameter_name]

    def get_output_objects(self, cls, exclude_parameters=None, *args, **kwargs):
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


class ModelFieldSearcher(DjangoProjectLookout):
    def get_output_object_fallback(self):
        return AbstractModelFieldWrapper(name=self.translator_to_en.translate(self.text))

    def get_keywords(self, field):
        return [field.name, getattr(field, 'verbose_name', None)]

    def get_output_objects(self, model_wrapper, *args, **kwargs):
        return model_wrapper.fields


class SerializerFieldSearcher(DjangoProjectLookout):
    def get_output_object_fallback(self):
        return AbstractApiFieldWrapper(name=self.translator_to_en.translate(self.text))

    def get_keywords(self, field):
        return [field.source]

    def get_output_objects(self, serializer, *args, **kwargs):
        if not serializer:
            return []

        return [ApiFieldWrapper(api_field=field) for field in serializer.fields.fields.values()]


class ModelSearcher(DjangoProjectLookout):
    def get_output_object_fallback(self):
        return AbstractModelWrapper(name=self.translator_to_en.translate(self.text))

    def get_keywords(self, model):
        return [model.name, model.verbose_name, model.verbose_name_plural]

    def get_output_objects(self, project_wrapper, *args, **kwargs):
        return project_wrapper.get_models(as_wrapper=True, include_django=True)


class PermissionSearcher(DjangoProjectLookout):
    """Can search for specific permissions in Django."""

    def get_output_object_fallback(self):
        return None

    def get_keywords(self, permission):
        return [permission.codename, permission.name]

    def get_output_objects(self, *args, **kwargs):
        return Permission.objects.all()


class UrlSearcher(DjangoProjectLookout):
    """
    This lookout will find urls in the django project.
    """
    def __init__(self, text, language, model_wrapper, valid_methods):
        super().__init__(text, language)
        self.model_wrapper = model_wrapper

        if Methods.PUT in valid_methods:
            valid_methods = valid_methods.copy()
            valid_methods.append(Methods.PATCH)

        self.valid_methods = [method for method in valid_methods if method]

    def get_output_object_fallback(self):
        return AbstractUrlPatternWrapper(model_wrapper=self.model_wrapper)

    def go_to_next_output(self, similarity):
        return similarity > 0.9

    def is_new_fittest_output_object(self, similarity, url_wrapper, input_doc, output_doc):
        """
        For different urls there might be multiple endpoints with the same methods. To identify which one is meant,
        the reverse name and url name is used to determine which endpoint is better suited.
        """
        fittest_url = self.fittest_output_object

        if fittest_url and similarity == self.highest_similarity and url_wrapper != fittest_url:
            best_similarity = 0
            best_conv = fittest_url

            for conv in [fittest_url, url_wrapper]:
                reverse_url_name_translated = self.translator_to_src.translate(conv.reverse_url_name)
                reverse_name_translated = self.translator_to_src.translate(conv.reverse_name)

                for check in [reverse_name_translated, reverse_url_name_translated]:
                    exact_similarity = self.get_similarity(input_doc, self.nlp_src_language(check))
                    if exact_similarity > best_similarity:
                        best_conv = conv
                        best_similarity = exact_similarity

            # sometimes we are not provided with the reverse url name but only the method; if there are default
            # api routes by an ApiView, use them instead
            conversion_default_route = url_wrapper.reverse_url_name in ['detail', 'list']
            fittest_conversion_default_route = fittest_url.reverse_url_name in ['detail', 'list']
            if best_similarity < 0.4 and conversion_default_route and not fittest_conversion_default_route:
                best_conv = url_wrapper

            return best_conv == url_wrapper

        return super().is_new_fittest_output_object(similarity, url_wrapper, input_doc, output_doc)

    def get_keywords(self, url_wrapper):
        keywords = [url_wrapper.reverse_url_name, url_wrapper.reverse_name]

        if url_wrapper.method_is_supported(Methods.GET):
            keywords += RestActionLocator.GET_KEYWORDS

        if url_wrapper.method_is_supported(Methods.POST):
            keywords += RestActionLocator.CREATE_KEYWORDS

        if url_wrapper.method_is_supported(Methods.PUT) or url_wrapper.method_is_supported(Methods.PATCH):
            keywords += RestActionLocator.UPDATE_KEYWORDS

        if url_wrapper.method_is_supported(Methods.DELETE):
            keywords += RestActionLocator.DELETE_KEYWORDS

        return keywords

    def get_output_objects(self, django_project, *args, **kwargs):
        url_patterns = django_project.list_urls(as_pattern=True)
        results = []

        for pattern in url_patterns:
            wrapper = UrlPatternWrapper(pattern)

            if wrapper.is_represented_by_view_set:
                # if the url does not have a valid method, skip it
                # if there are no valid methods provided, allow all
                if self.valid_methods and not any([m in self.valid_methods for m in wrapper.methods]):
                    continue

                # if the model is not the same, skip it
                if wrapper.model_wrapper.model != self.model_wrapper.model:
                    continue

                results.append(wrapper)

        return results

