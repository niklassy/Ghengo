from nlp.settings import SIMILARITY_BENCHMARK


def are_synonyms(input_1, input_2):
    """Check if two tokens are synonyms."""
    return input_1.similarity(input_2) > SIMILARITY_BENCHMARK


def get_non_stop_tokens(doc):
    """Reduce to the most important content."""
    return [t for t in doc if not t.is_stop]


def get_named_entities(doc):
    """Useful to find names in a doc"""
    return doc.ents


def get_nouns_chunks(doc):
    """Get all chunks of the doc that are nouns."""
    return [n for n in doc.noun_chunks]
