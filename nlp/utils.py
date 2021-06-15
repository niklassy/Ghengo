from nlp.settings import SIMILARITY_BENCHMARK


def are_synonyms(input_1, input_2):
    """Check if two tokens are synonyms."""
    if not input_1.vector_norm or not input_2.vector_norm:
        return False

    return input_1.similarity(input_2) > SIMILARITY_BENCHMARK


def get_non_stop_tokens(doc):
    """Reduce to the most important content."""
    return [t for t in doc if not t.is_stop]


def get_named_entities(doc):
    """Useful to find names in a doc"""
    return doc.ents


def get_noun_chunks(doc):
    """Get all chunks of the doc that are nouns."""
    return [n for n in doc.noun_chunks]


def token_references(token, target):
    """
    Check if a token references another token.
    """
    return token.head == target


def is_proper_noun_of(token, target):
    """
    Check if a given token references another noun. These tokens are called proper nouns and are things like:
    `alice` or `todo1`.

    => Given a user alice.
    """
    return token_references(token, target) and token.pos_ == 'PROPN'


def token_in_span(token, span):
    return token in span


def get_referenced_entity(token):
    if not bool(token.ent_type_):
        if token == token.head or not token.head:
            return None

        return get_referenced_entity(token.head)
    return token


def get_verb_for_token(token):
    if token.pos_ == 'VERB':
        return token

    if token.head is None or token.head == token:
        return None

    return get_verb_for_token(token.head)


def get_noun_chunk_of_token(token, document):
    for chunk in get_noun_chunks(document):
        if token in chunk:
            return chunk
    return None
