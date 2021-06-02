def are_synonyms(token_1, token_2):
    """Check if two tokens are synonyms."""
    return token_1.similarity(token_2) > 0.6


def get_non_stop_tokens(doc):
    """Reduce to the most important content."""
    return [t for t in doc if not t.is_stop]


def get_named_entities(doc):
    """Useful to find names in a doc"""
    return doc.ents


def get_nouns_chunks(doc):
    """Get all chunks of the doc that are nouns."""
    return [n for n in doc.noun_chunks]
