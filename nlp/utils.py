import zahlwort2num as w2n_de
from word2number import w2n as w2n_en

from core.constants import Languages
from core.exception import LanguageNotSupported
from nlp.generate.utils import to_function_name
from nlp.vocab import NEGATIONS, LIKE_NUM_WORDS, NUM_END_VARIATIONS


class NoToken:
    children = []
    is_digit = False
    lang_ = None
    tag_ = None
    pos_ = None
    morph = ''
    i = 0

    def __eq__(self, other):
        return False

    def __bool__(self):
        return False

    def __str__(self):
        return ''


def get_next_token(token):
    """
    Returns the token that follows the one that is passed to the function. If there is none, a NoToken instance is
    returned.
    """
    try:
        return token.doc[token.i + 1]
    except IndexError:
        return NoToken()


def tokens_are_equal(token_1, token_2):
    """
    Check if two tokens are equal. This method is needed because if tokens are compared via == and one of them
    is a NoToken, the Token from spacy does not know how to handle it.
    """
    if isinstance(token_1, NoToken) or isinstance(token_2, NoToken):
        return False

    return token_1 == token_2


def get_previous_token(token):
    """
    Returns the token that is behind the one that is passed to the function. If there is none, a NoToken instance is
    returned.
    """
    try:
        if token.i == 0:
            return NoToken()

        return token.doc[token.i - 1]
    except IndexError:
        return NoToken()


def token_can_represent_variable(token):
    return token_is_proper_noun(token) or token.is_digit or is_quoted(token)


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


def get_propn_from_previous_chunk(token):
    """
    Returns a proper noun from a previous noun chunk.
    """
    document = token.doc
    chunk = get_noun_chunk_of_token(token, document)

    if not chunk:
        return NoToken()

    noun_chunks = get_noun_chunks(document)

    try:
        chunk_index = noun_chunks.index(chunk)  # <- can raise ValueError if not in chunk
        previous_chunk = noun_chunks[chunk_index - 1]  # <- can raise IndexError if no previous chunk
        previous_propn = get_proper_noun_from_chunk(previous_chunk)

        # only return if the previous chunk only contains the propn and no noun
        if get_noun_from_chunk(previous_chunk) is None and previous_propn:
            return previous_propn
    except (IndexError, ValueError):
        return NoToken()


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
    return bool(get_negation_token(token))


def get_negation_token(token):
    """Returns the token that negates the given one. If there is none, a NoToken is returned."""
    for child in token.children:
        if token_represents_negation(child):
            return child

    return NoToken()


def token_represents_negation(token):
    """Check if a token represents a negation."""
    return token.lemma_ in NEGATIONS[token.lang_]


def token_is_indefinite(token):
    """Check if a token is indefinite (unbestimmt => ein, einen etc.)."""
    return 'Definite=Ind' in token.morph


def token_is_definite(token):
    """Check if a token is definite (bestimmt => der, das etc.)."""
    return 'Definite=Def' in token.morph


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


def num_word_to_integer(num_word, language):
    """
    Changes a word into a number. (Like two => 2)

    :raises LanguageNotSupported - provided language is not supported yet
    :raises ValueError - word cannot be converted
    """
    if language not in Languages.get_supported_languages():
        raise LanguageNotSupported()

    if language == Languages.DE:
        try:
            output = w2n_de.convert(num_word)
        except KeyError:
            raise ValueError('No value found')

    else:
        output = w2n_en.word_to_num(num_word)

    if isinstance(output, int):
        return output

    return ''.join(c for c in output if c.isdigit())


def token_is_plural(token):
    return token_is_noun(token) and 'Number=Plur' in token.morph


def token_is_like_num(token):
    """
    Checks if a given token is like a number (two, zwei etc.)
    """
    text = str(token)

    if isinstance(token, NoToken):
        return False

    # some tokens already have the value set, this does not work well for non english languages though
    if token.like_num:
        return True

    if text.startswith(("+", "-", "±", "~")):
        text = text[1:]

    text = text.replace(",", "").replace(".", "")
    if text.isdigit():
        return True

    if text.count("/") == 1:
        num, denom = text.split("/")
        if num.isdigit() and denom.isdigit():
            return True

    text_lower = text.lower()
    lemma_lower = str(token.lemma_).lower()
    try:
        num_word_to_integer(lemma_lower, token.lang_)
        return token.pos_ == 'NUM' or token.pos_ == 'ADJ' or token.pos_ == 'DET'
    except (ValueError, LanguageNotSupported):
        try:
            num_word_to_integer(text_lower, token.lang_)
            return token.pos_ == 'NUM' or token.pos_ == 'ADJ' or token.pos_ == 'DET'
        except (ValueError, LanguageNotSupported):
            pass

    try:
        if text_lower in LIKE_NUM_WORDS[token.lang_].keys():
            return True

        for end_variation in NUM_END_VARIATIONS[token.lang]:
            if text_lower[:-len(end_variation)].isdigit():
                return True
    except KeyError:
        pass

    return False
