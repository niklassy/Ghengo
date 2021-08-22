from gherkin.compiler_base.symbol import Symbol


class TerminalSymbol(Symbol):
    """
    This is a wrapper for defining rules. It is a wrapper around any custom class that is used while defining
    rules. For this project, the class could be removed, but it is a nice wrapper for future usage.
    """
    def __init__(self, token_cls):
        super().__init__()
        self.token_cls = token_cls

    def get_next_valid_tokens(self):
        return [self.token_cls]

    def sequence_to_object(self, sequence, index=0):
        """This alias represents a simple token - so just return at the index that we are at."""
        # everything is validated before this is called, so this should always be the same!
        assert sequence[index].token.__class__ == self.token_cls

        return sequence[index]

    def token_wrapper_is_valid(self, token_wrapper) -> bool:
        """
        Check if a given token_wrapper belongs to the class that this wrapper represents. Used by rules to check if a
        value is valid for this class.
        """
        return isinstance(token_wrapper.token, self.token_cls)

    def get_keywords(self) -> [str]:
        """
        Return a list of keywords. Used by rules to see what keywords are expected. So: what is expected to be found
        for this class? How can this token be represented as a string?
        """
        return self.token_cls.get_keywords()

    def __str__(self):
        return str(self.token_cls)

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return self.token_cls == other.token_cls
