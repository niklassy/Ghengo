from gherkin.compiler_base.terminal import TerminalSymbol


class TokenWrapper(object):
    """
    This is a wrapper around any custom token object. It is used to allow rules to get the line_number and the
    text of a token. For this project, the class could be removed, but it is a nice wrapper for future usage.
    """
    def __init__(self, token):
        self.token = token
        self.terminal_symbol = TerminalSymbol(token.__class__)

    def get_place_to_search(self) -> str:
        """Is used by rules to add information where a token can be found."""
        return 'Near line: {}'.format(self.token.line.line_index + 1)

    def get_text(self) -> str:
        """Defines how to represent a token in text. It is used by rules to display what the current value is."""
        return self.token.matched_keyword

    def __str__(self):
        return str(self.token)

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False

        return self.token == other.token
