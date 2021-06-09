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
            raise NoConversionFound('No field was found')

        return fittest_conversion


class TextToModelFieldConverter(TextConverter):
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


# def get_model_field_by_text(language, text, model_interface, related_field=False):
#     """
#     This function can be used to find a field in a model that fits a given string in a given language.
#     Example:
#         language = de
#         text = Vorname
#         model_interface = ModelInterface of some model
#
#         This function will translate the text to english (because it is assumed that fields are named in english).
#         It will then iterate over all fields of the model to find the best field. If the similarity is too low or
#         no field is found, None is returned.
#     """
#     translator = GoogleTranslator(source=language, target='en')
#     en_word = translator.translate(text)
#     nlp = Nlp.for_language('en')
#     orig_nlp = Nlp.for_language(language)
#     en_doc = nlp(en_word)
#     orig_doc = orig_nlp(text)
#
#     highest_similarity = 0
#     fittest_field = None
#
#     for field in model_interface.fields:
#         verbose_name = getattr(field, 'verbose_name', None)
#         field_name = field.name
#
#         # check verbose name and name
#         comparisons = [
#             (en_doc, nlp(field_name.replace('_', ' '))),
#             (orig_doc, orig_nlp(field_name.replace('_', ' '))),
#         ]
#
#         if bool(verbose_name):
#             comparisons.append((en_doc, nlp(verbose_name.replace('_', ' '))))
#             comparisons.append((orig_doc, orig_nlp(verbose_name.replace('_', ' '))))
#
#         for input_doc, field_name_doc in comparisons:
#             if not input_doc.vector_norm or not field_name_doc.vector_norm:
#                 continue
#
#             similarity = input_doc.similarity(field_name_doc)
#             if similarity > highest_similarity:
#                 fittest_field = field
#                 highest_similarity = similarity
#
#     if highest_similarity <= SIMILARITY_BENCHMARK or fittest_field is None:
#         raise ValueError('No field was found')
#
#     return fittest_field
#
#
# def get_model_from_text(language, text, project_interface, **kwargs):
#     """Find a model from a given text."""
#     models = project_interface.get_models(as_interface=True, include_django=True, **kwargs)
#     translator = GoogleTranslator(source=language, target='en')
#     en_word = translator.translate(text)
#     nlp_en = Nlp.for_language('en')
#     nlp_orig = Nlp.for_language(language)
#     en_doc = nlp_en(en_word)
#
#     # get original language
#     orig_doc = nlp_orig(text)
#
#     highest_similarity = 0
#     fittest_model = None
#
#     for model in models:
#         # handle english and german from both sides
#         verbose_name = model.verbose_name
#         name = model.name
#
#         comparisons = [
#             (en_doc, nlp_en(name)),
#             (orig_doc, nlp_orig(name)),
#         ]
#
#         if bool(verbose_name):
#             comparisons.append((en_doc, nlp_en(verbose_name)))
#             comparisons.append((orig_doc, nlp_orig(verbose_name)))
#
#         for input_doc, field_name_doc in comparisons:
#             if not input_doc.vector_norm or not field_name_doc.vector_norm:
#                 continue
#
#             similarity = input_doc.similarity(field_name_doc)
#             if similarity > highest_similarity:
#                 fittest_model = model
#                 highest_similarity = similarity
#
#     if highest_similarity <= SIMILARITY_BENCHMARK or fittest_model is None:
#         raise ValueError('No model was found')
#
#     return fittest_model

#
# def handle_given(project, language, given):
#     nlp = Nlp.for_language(language)
#     doc = nlp(str(given))
#     model = None
#     field_values = []
#
#     for i, span in enumerate(get_nouns_chunks(doc)):
#         if i == 0:
#             model = get_model_from_text(language, str(span.root), project)
#             continue
#
#         # handle normal fields
#         try:
#             field = get_model_field_by_text(language, str(span.root), model)
#         except ValueError:
#             continue
#
#         value = None
#         for token in span:
#             if token.head == span.root:
#                 value = token
#
#         if value is None:
#             continue
#
#         field_values.append((field, value))
#
#     # TODO: handle fk fields
#     # for token in get_non_stop_tokens(doc):
#     #     # TODO: how to handle different languages
#     #     if are_synonyms(token, Nlp.for_language('de')('Zuordnung')):
#     #         current_head = token.head
#     #         while current_head not in [t for _, t in field_values]:
#     #             current_head = current_head.head
#     #         # TODO: find field somehow
#
#     return model, field_values
