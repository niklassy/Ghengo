import re
from unidecode import unidecode


def camel_to_snake_case(string, allowed_characters=None):
    """Transform camel case to snake case."""
    if allowed_characters is None:
        allowed_characters = []

    no_special = ''.join(e if e.isalnum() or e in allowed_characters else '' for e in string)
    reg_ex = re.compile('((?<=[a-z0-9])[A-Z]|(?!^)[A-Z](?=[a-z]))')
    return reg_ex.sub(r'_\1', no_special).lower()


def to_function_name(string):
    """
    Turns a string into a valid function name. It will remove remove non-ascii characters, whitespaces
    and transform everything into lower case.
    """
    if not isinstance(string, str):
        return ''

    no_special = remove_non_alnum(
        camel_to_snake_case(string, allowed_characters=['_']),
        replace_character=' ',
        allowed_characters=['_'],
    )
    non_ascii = remove_non_ascii(no_special)

    if not non_ascii:
        return ''

    while non_ascii[0].isdigit():
        non_ascii = non_ascii[1:]

        if not non_ascii:
            break

    return '_'.join(non_ascii.split())


def remove_non_alnum(string, replace_character='', allowed_characters=None):
    """Removes all characters in a string that are not numbers or characters"""
    if allowed_characters is None:
        allowed_characters = []

    return ''.join(e if e.isalnum() or e in allowed_characters else replace_character for e in string.lower())


def remove_non_ascii(text):
    """Replaces all non ascii characters with similar characters (e.g. ß => ss, ä => ae)"""
    return unidecode(str(text))
