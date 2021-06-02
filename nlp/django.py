from translate import Translator

from nlp.settings import SIMILARITY_BENCHMARK
from nlp.setup import Nlp


def get_model_field_by_text(language, text, model_interface):
    """
    This function can be used to find a field in a model that fits a given string in a given language.
    Example:
        language = de
        text = Vorname
        model_interface = ModelInterface of some model

        This function will translate the text to english (because it is assumed that fields are named in english).
        It will then iterate over all fields of the model to find the best field. If the similarity is too low or
        no field is found, None is returned.
    """
    translator = Translator(from_lang=language, to_lang='en')
    en_word = translator.translate(text)
    nlp = Nlp.for_language('en')
    en_doc = nlp(en_word)

    highest_similarity = 0
    fittest_field = None

    for field in model_interface.fields:
        verbose_name = field.verbose_name
        field_name = field.name
        name = verbose_name or field_name

        # transform the python definition to "normal" english and apply nlp
        name = name.replace('_', ' ')
        field_doc = nlp(name)

        similarity = en_doc.similarity(field_doc)

        if similarity > highest_similarity:
            fittest_field = field
            highest_similarity = similarity

    if highest_similarity <= SIMILARITY_BENCHMARK:
        return None

    return fittest_field
