from nlp.lookout.base import Lookout
from nlp.lookout.exception import LookoutFoundNothing


class NestedLookout(Lookout):
    """
    This lookout can be used to apply several other lookouts at once and get the best result from all of them.
    """
    # we don't ever want an error when calling locate
    similarity_benchmark = 0

    def __init__(self, lookout_child_classes, texts, language, locate_kwargs):
        super().__init__('', language)
        self.lookout_child_classes = list(set(lookout_child_classes))
        self.texts = texts
        self.locate_kwargs = locate_kwargs
        self._lookout_child_instances = None

    def get_keywords(self, output_object):
        """
        Returns all the texts as a list here. This will make it easier to get the similarity of children.
        """
        return [self.texts]

    def get_output_objects(self, *args, **kwargs):
        """All the classes are used **initially** as output objects. Later on the instance is used instead."""
        return self.lookout_child_classes

    def get_fallback(self):
        return None

    def go_to_next_output(self, similarity):
        return self.highest_similarity > 0.9

    def is_new_fittest_output_object(self, similarity, output_object, input_doc, output_doc):
        """
        Make sure that there is at least one output by settings the value if there is none already.
        """
        if self._fittest_output_object is None:
            return True

        # else use the similarity normally
        return super().is_new_fittest_output_object(similarity, output_object, input_doc, output_doc)

    def get_compare_variations(self, lookout_cls, texts):
        """
        Here we have to chat a little bit.
        """
        variations = []

        last_lookout_class = self.lookout_child_classes.index(lookout_cls) == len(self.lookout_child_classes) - 1
        for text_index, text in enumerate(texts):

            # only raise no exception if it is the last lookout class and the last text to have a fallback
            last_search_text = text_index == len(texts) - 1
            raise_exception = not last_search_text or not last_lookout_class

            lookout = lookout_cls(text, self.src_language)
            try:
                lookout.locate(raise_exception=raise_exception, **self.locate_kwargs)

                # !!! set the lookout here for access later !!!
                variations.append((lookout, None))
            except LookoutFoundNothing:
                pass

        return variations

    def get_similarity(self, lookout, target_doc):
        """
        Simply return the highest similarity from the lookout object. The first object is a lookout here
        since we set the value in `get_compare_variations`.
        """
        return lookout.highest_similarity

    def on_new_fittest_output_object_found(self, similarity, output_object, keyword, input_1, input_2):
        """
        Overwrite the _fittest_output_object to be the lookout **instance** which can be found in input_1
        (see `get_compare_variations`).
        """
        super().on_new_fittest_output_object_found(similarity, output_object, keyword, input_1, input_2)

        # input_1 is here the lookout instance
        self._fittest_output_object = input_1

    def locate(self, *args, **kwargs):
        """
        Never raise an exception.
        """
        return super().locate(*args, raise_exception=False, **kwargs)

    @property
    def fittest_keyword(self):
        """Return the fittest keyword of the child."""
        nested_lookout = self.fittest_output_object

        if nested_lookout is None:
            return None

        return nested_lookout.fittest_keyword

    @property
    def fittest_output_object(self):
        """Return the nested output."""
        nested_lookout = super().fittest_output_object

        if nested_lookout is None:
            return nested_lookout

        return nested_lookout.fittest_output_object

