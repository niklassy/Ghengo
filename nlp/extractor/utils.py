from nlp.extractor.exception import ExtractionError
from nlp.extractor.vocab import POSITIVE_BOOLEAN_INDICATORS
from nlp.generate.warning import BOOLEAN_NO_SOURCE
from nlp.utils import get_verb_for_token, token_is_negated


def extract_boolean(token, document):
    """
    Extracts a python boolean value from a token.
    """
    if isinstance(token, str) or token is None:
        verb = None
    else:
        verb = get_verb_for_token(token)

    if not verb:
        if not token:
            raise ExtractionError(BOOLEAN_NO_SOURCE)

        return str(token) in POSITIVE_BOOLEAN_INDICATORS[document.lang_]

    return not token_is_negated(verb) and not token_is_negated(token)
