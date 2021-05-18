from typing import Optional

from gherkin.compiler_base.line import Line


class Token(object):
    """
    A token represents a collection of characters in a text. If will be used later by the parser to check the
    validity. In our case, tokens are lines because Gherkin only has one `statement` per line.
    """
    # does the keyword have a `:` at the end?
    keyword_with_colon = False

    def __init__(self, text: Optional[str], line: Optional[Line]):
        self.line: Optional[Line] = line

        self.text: Optional[str] = text
        self.matched_keyword_full = self.reduce_to_belonging(text) if text else None

        if self.keyword_with_colon and self.matched_keyword_full:
            self.matched_keyword = self.matched_keyword_full.replace(':', '')
        else:
            self.matched_keyword = self.matched_keyword_full

    @classmethod
    def get_matching_keyword(cls, string: str):
        """Returns the keyword that matches a string. If there is none, it returns None."""
        for keyword in cls.get_keywords():
            if string.startswith(keyword):
                return keyword
        return None

    @classmethod
    def reduce_to_belonging(cls, string: str):
        """Given a string, this will return everything of it that belongs to this token."""
        return cls.get_matching_keyword(string)

    @classmethod
    def string_contains_token(cls, string: str):
        """Checks if a given string contains this token."""
        return bool(cls.get_matching_keyword(string))

    @classmethod
    def get_keywords(cls):
        """Returns all the keywords that identify a token."""
        raise NotImplementedError()

    def __repr__(self):
        return '{}-Token: "{}" in {}'.format(self.__class__.__name__, self.matched_keyword_full, self.line)
