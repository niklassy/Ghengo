import re
from unidecode import unidecode


def camel_to_snake_case(string):
    """Transform camel case to snake case."""
    reg_ex = re.compile('((?<=[a-z0-9])[A-Z]|(?!^)[A-Z](?=[a-z]))')
    return reg_ex.sub(r'_\1', string).lower()


def to_function_name(string):
    """
    Pass in a string to return it into a function name in snake case. It will remove non-ascii characters, whitespaces
    and transform everything into lower case.
    """
    no_special = ''.join(e if e.isalnum() else ' ' for e in string.lower())
    non_ascii = remove_non_ascii(no_special)
    return '_'.join(non_ascii.split())


def remove_non_ascii(text):
    """Replaces all non ascii characters with similar characters (e.g. ß => ss, ä => ae)"""
    return unidecode(str(text))
