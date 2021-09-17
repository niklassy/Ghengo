from core.constants import Languages
from nlp.lookout.exception import LookoutFoundNothing
from nlp.setup import Nlp
from nlp.translator import CacheTranslator


class Lookout(object):
    """
    The lookout class can be used to find something with a given text. It will check the text and compare it to
    keywords. Each lookout has defined output objects that can be found.

    Since the lookout will have several keywords and several variations of keywords, the locating can be
    quite expensive. Therefore there are several methods to optimize the process.
    """
    # the minimum similarity value to find a value
    similarity_benchmark = 0.5

    def __init__(self, text, src_language, locate_on_init=False, *args, **kwargs):
        self.text = text
        self.src_language = src_language

        # some private values for properties
        self._translator_to_en = None
        self._translator_to_src = None
        self._doc_src_language = None
        self._doc_en = None
        self._highest_similarity = 0
        self._fittest_output_object = None
        self._fittest_keyword = None
        self._results_in_fallback = False

        # normally the locate() is not done on init because of the performance reasons, you can call it on init
        # though
        if locate_on_init:
            self.locate(*args, **kwargs)

    @property
    def results_in_fallback(self):
        return self._results_in_fallback

    def get_similarity_benchmark(self):
        """A wrapper around the benchmark for the similarity."""
        return self.similarity_benchmark

    @property
    def translator_to_en(self):
        """
        The lookout has to translate keywords and values. This is its own translator for the source language
        to english.
        """
        if self._translator_to_en is None:
            self._translator_to_en = CacheTranslator(src_language=self.src_language, target_language=Languages.EN)
        return self._translator_to_en

    @property
    def translator_to_src(self):
        """The translator english -> src"""
        if self._translator_to_src is None:
            self._translator_to_src = CacheTranslator(src_language=Languages.EN, target_language=self.src_language)
        return self._translator_to_src

    @property
    def nlp_en(self):
        """Returns the callable to apply NLP in english."""
        return Nlp.for_language(Languages.EN)

    @property
    def nlp_src_language(self):
        """Returns the callable to apply NLP in the src language."""
        return Nlp.for_language(self.src_language)

    @property
    def doc_src_language(self):
        """Returns the document in the correct language."""
        if self._doc_src_language is None:
            self._doc_src_language = self.nlp_src_language(self.text)
        return self._doc_src_language

    @property
    def doc_en(self):
        """Returns the text translated to english as an english document."""
        if self._doc_en is None:
            self._doc_en = self.nlp_en(self.translator_to_en.translate(self.text))
        return self._doc_en

    def get_compare_variations(self, output_object, keyword):
        """
        Returns a tuple of values. Each entry will be compared by calling `get_similarity`.

        :argument output_object - one of the objects that are returned from `get_output_objects`
        :argument keyword - one of the keywords that are returned from `get_keywords`
        :returns [(doc_1, doc_2)]
        """
        return []

    def get_similarity(self, input_doc, target_doc):
        """Returns the similarity between two docs/ tokens in a range from 0 - 1."""
        raise NotImplementedError()

    @property
    def highest_similarity(self):
        """Returns the highest similarity that was returned after `locate` was called."""
        return self._highest_similarity

    @property
    def fittest_output_object(self):
        """
        Returns the fittest output_object that was returned after `locate` was called. This will be either
        the value that is returned from `get_fallback` or a value from `get_output_objects`
        """
        return self._fittest_output_object

    @property
    def fittest_keyword(self):
        """
        Returns the fittest keyword that had the highest similarity after using `locate`. This will either be None
        or one of the values from `get_keywords`.
        """
        return self._fittest_keyword

    def get_keywords(self, output_object):
        """
        Should return a list of keywords that will be used for the similarity later on.
        """
        raise NotImplementedError()

    def get_output_objects(self, *args, **kwargs):
        """
        Returns all the possible output objects that this can return.
        """
        raise NotImplementedError()

    def output_object_is_relevant(self, output_object):
        """
        Check if a output_object is relevant given certain circumstances.
        """
        return True

    def should_stop_looking_for_output(self):
        """
        If this returns true, locate will stop looking at future output objects and simply return what is found.
        This will be checked after each object output.
        """
        return self.highest_similarity >= 1

    def go_to_next_output(self, similarity):
        """
        If this is true, locate will stop looking at a given output_object and go to the next one. This is called
        after the similarity has been checked.
        """
        return similarity >= 1

    def prepare_keywords(self, keywords):
        """
        Is called before the keywords are passed to `get_compare_variations`. It can be used to modify the
        keywords.
        """
        return keywords

    def is_new_fittest_output_object(self, similarity, output_object, input_doc, output_doc):
        """
        If this returns true, the output_object will be taken as the new self.fittest_output_object.
        """
        return similarity > self.highest_similarity

    def get_fallback(self):
        """
        In case the similarity benchmark is not met over all output_objects, this is used to return an object
        if raise_exception in `locate` is False.
        """
        raise NotImplementedError()

    def reset_fittest_output_object(self):
        """
        Locate will cache the result. You can use this method to reset the cache.
        """
        self._fittest_output_object = None

    def on_new_fittest_output_object_found(self, similarity, output_object, keyword, input_1, input_2):
        """
        Is called after a new best output_object has been found.
        """
        self._highest_similarity = similarity
        self._fittest_output_object = output_object
        self._fittest_keyword = keyword

    def has_invalid_fittest_output(self):
        """
        Check if this lookout has an invalid output. If this is true, this would normally result in a fallback
        object or an exception.
        """
        return self.highest_similarity < self.get_similarity_benchmark() or self.fittest_output_object is None

    def locate(self, *args, raise_exception=False, **kwargs):
        """
        The main function that looks for the fittest_output_object.

        If raise_exception is true, no fallback will be returned if the similarity benchmark is not met. There will
        a LookoutFoundNothing exception instead.
        """
        if self.fittest_output_object is not None:
            return self.fittest_output_object

        self._results_in_fallback = False

        for output_object in self.get_output_objects(*args, **kwargs):
            # if we should stop, end the loop
            if self.should_stop_looking_for_output():
                break

            # if the object is not relevant, go to the next
            if not self.output_object_is_relevant(output_object):
                continue

            # get and prepare the keywords
            keywords = self.get_keywords(output_object)
            prepared_keywords = self.prepare_keywords(keywords)

            for keyword in prepared_keywords:
                # get all the variations
                variations = self.get_compare_variations(output_object, keyword)

                for value_1, value_2 in variations:
                    # get the similarity and check if the object is better than previous ones
                    similarity = self.get_similarity(value_1, value_2)

                    if self.is_new_fittest_output_object(similarity, output_object, value_1, value_2):
                        self.on_new_fittest_output_object_found(
                            similarity=similarity,
                            input_1=value_1,
                            input_2=value_2,
                            output_object=output_object,
                            keyword=keyword,
                        )

                    if self.go_to_next_output(similarity):
                        break

        # if the highest_similarity is too low, overwrite the values and raise an exception if wanted
        if self.has_invalid_fittest_output():
            # has to stay before raise_exception!
            self._fittest_output_object = self.get_fallback()
            self._fittest_keyword = None
            self._results_in_fallback = True

            if raise_exception:
                raise LookoutFoundNothing()

        return self.fittest_output_object
