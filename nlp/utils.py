from nlp.generate.utils import to_function_name
from nlp.vocab import NEGATIONS


class NoToken:
    children = []
    is_digit = False

    def __eq__(self, other):
        return False

    def __bool__(self):
        return False

    def __str__(self):
        return ''


def get_non_stop_tokens(doc):
    """Reduce to the most important content."""
    return [t for t in doc if not t.is_stop]


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
    return token_references(token, target) and token_is_proper_noun(token)


def get_verb_for_token(token):
    """Returns the that belongs to a given token."""
    if token_is_verb(token):
        return token

    if token.head is None or token.head == token:
        return NoToken()

    return get_verb_for_token(token.head)


def get_proper_noun_of_chunk(token, chunk):
    """Returns the proper noun of a given noun chunk."""
    for t in chunk:
        if is_proper_noun_of(t, token):
            return t
    return None


def get_noun_chunk_of_token(token, document):
    """
    Returns the noun chunk of a given token.
    """
    for chunk in get_noun_chunks(document):
        if token in chunk:
            return chunk
    return None


def token_is_noun(token):
    """
    Check if a token is a noun.
    """
    return token.pos_ == 'NOUN'


def token_is_proper_noun(token):
    """
    Check if a token is a proper noun.

    Proper nouns are names of nouns like persons, places etc. (like Alice, Bob...)
    """
    return token.pos_ == 'PROPN'


def get_proper_noun_from_chunk(chunk):
    for t in chunk:
        if token_is_proper_noun(t):
            return t
    return None


def get_noun_from_chunk(chunk):
    for t in chunk:
        if token_is_noun(t):
            return t
    return None


def is_quoted(token):
    """Check if a given input is quoted."""
    string = str(token) if token else ''
    if len(string) < 3:
        return False

    return (string[0] == '"' and string[-1] == '"') or (string[0] == '\'' and string[-1] == '\'')


def token_is_negated(token):
    """Check if a token is negated."""
    return any([child for child in token.children if child.lemma_ in NEGATIONS[token.lang_]])


def token_is_verb(token, include_aux=True):
    """
    Returns if a token is a verb.

    AUX means auxiliary verbs. Those are words like:
        - de: (sein, haben, tun...)
        - en: (will, do...)
    """
    if not include_aux:
        return token.pos_ == 'VERB'

    return token.pos_ == 'VERB' or token.pos_ == 'AUX'


def get_all_children(token, prefilled_list=None):
    """Returns all children and sub-children of a token."""
    if not token:
        return []

    output = prefilled_list if prefilled_list is not None else []

    for child in token.children:
        output.append(child)
        get_all_children(child, output)

    return output


def get_root_of_token(token):
    if token.dep_ == 'ROOT':
        return token

    if not token.head or token.head == token:
        return None

    return get_root_of_token(token.head)


def token_to_function_name(token):
    """Translates a token to a function name."""
    token_str = str(token)
    if token.is_digit:
        return token_str

    if is_quoted(token):
        token_str = token_str[1:-1]

    return to_function_name(token_str)
