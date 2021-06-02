import nltk
import spacy

# nlp_en = spacy.load("en_core_web_trf")
# nlp_de = spacy.load("de_dep_news_trf")

# nltk.download('popular')
def setup_nlp():
    # nltk.download('punkt')
    # nltk.download('words')
    # nltk.download('wordnet')
    # nltk.download('maxent_ne_chunker')
    # nltk.download('averaged_perceptron_tagger')
    # andere Alternative: de_dep_news_trf en_core_web_trf
    return spacy.load("en_core_web_lg"), spacy.load("de_core_news_lg")


def get_nlp_for_language(lang):
    if lang == 'de':
        return spacy.load('de_core_news_lg')

    return spacy.load('en_core_web_lg')

