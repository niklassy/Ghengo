import re


def camel_to_snake_case(string):
    """Transform camel case to snake case."""
    reg_ex = re.compile('((?<=[a-z0-9])[A-Z]|(?!^)[A-Z](?=[a-z]))')
    return reg_ex.sub(r'_\1', string).lower()
