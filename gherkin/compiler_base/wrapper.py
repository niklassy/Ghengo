class RuleAlias(object):
    """
    This is a wrapper for defining rules. It is a wrapper around any custom class that is used while defining
    rules. For this project, the class could be removed, but it is a nice wrapper for future usage.
    """
    def __init__(self, token_cls):
        self.token_cls = token_cls

    def rule_token_is_valid(self, rule_token: 'TokenWrapper') -> bool:
        """
        Check if a given rule_token belongs to the class that this wrapper represents. Used by rules to check if a
        value is valid for this class.
        """
        return isinstance(rule_token.token, self.token_cls)

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


class TokenWrapper(object):
    """
    This is a wrapper around any custom token object. It is used to allow rules to get the line_number and the
    text of a token. For this project, the class could be removed, but it is a nice wrapper for future usage.
    """
    def __init__(self, token):
        self.token = token
        self.rule_alias = RuleAlias(token.__class__)

    def get_place_to_search(self) -> str:
        """Is used by rules to add information where a token can be found."""
        return 'Near line: {}'.format(self.token.line.line_index)

    def get_text(self) -> str:
        """Defines how to represent a token in text. It is used by rules to display what the current value is."""
        return self.token.matched_keyword_full

    def __str__(self):
        return str(self.token)

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False

        return self.token == other.token
