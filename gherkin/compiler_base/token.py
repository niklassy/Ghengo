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
        """
        line = The line in which this token can be found
        text = the text inside the line that belongs to this token
        """
        self.line: Optional[Line] = line
        self.text: Optional[str] = text

        self.matched_keyword = self.get_matching_keyword(self.text)

        if self.matched_keyword is not None and self.text is not None:
            self.text_without_keyword = self.text.replace(self.matched_keyword, '', 1)
        else:
            self.text_without_keyword = self.text

        self._grammar_meta = {}

    def copy(self):
        return self.__class__(text=self.text, line=Line(text=self.line.text, line_index=self.line.line_index))

    @classmethod
    def string_matches_keyword(cls, string, keyword):
        """Check if a given keyword that was returned by `get_keywords` matches a string."""
        return string.startswith(keyword)

    @classmethod
    def get_matching_keyword(cls, string: str):
        """Returns the keyword that matches a string. If there is none, it returns None."""
        if string is None:
            return None

        for keyword in cls.get_keywords():
            if cls.string_matches_keyword(string, keyword):
                return keyword
        return None

    @classmethod
    def reduce_to_belonging(cls, string: str):
        """Given a string, this will return everything of it that belongs to this token."""
        return cls.get_matching_keyword(string) or ''

    @classmethod
    def string_contains_token(cls, string: str):
        """Checks if a given string contains this token."""
        return bool(cls.get_matching_keyword(string))

    @classmethod
    def get_keywords(cls):
        """Returns all the keywords that identify a token."""
        raise NotImplementedError()

    def get_meta_data_for_sequence(self, sequence):
        return {}

    @property
    def grammar_meta(self):
        return self._grammar_meta

    def set_grammar_meta_value(self, key, value):
        self._grammar_meta[key] = value

    def __repr__(self):
        return '{}: "{}" in {} (keyword: {})'.format(self.__class__.__name__, self.text, self.line, self.matched_keyword)

    def __str__(self):
        return self.text or ''
