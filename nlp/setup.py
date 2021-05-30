import nltk
import spacy

# nlp_en = spacy.load("en_core_web_trf")
# nlp_de = spacy.load("de_dep_news_trf")

# nltk.download('popular')
def setup_nlp():
    nltk.download('punkt')
    nltk.download('words')
    nltk.download('wordnet')
    nltk.download('maxent_ne_chunker')
    nltk.download('averaged_perceptron_tagger')
    return spacy.load("en_core_web_trf"), spacy.load("de_dep_news_trf")
