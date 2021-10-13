from typing import Optional

from gherkin.compiler_base.line import Line


class Token(object):
    """
    A token represents a collection of characters in a text. If will be used later by the parser to check the
    validity. In our case, tokens are lines because Gherkin only has one `statement` per line.
    """
    # does the pattern have a `:` at the end?
    pattern_with_colon = False

    def __init__(self, text: Optional[str], line: Optional[Line]):
        """
        line = The line in which this token can be found
        text = the text inside the line that belongs to this token
        """
        self.line: Optional[Line] = line
        self.lexeme: Optional[str] = text

        self.matched_pattern = self.get_matching_pattern(self.lexeme)

        if self.matched_pattern is not None and self.lexeme is not None:
            self.text_without_pattern = self.lexeme.replace(self.matched_pattern, '', 1)
        else:
            self.text_without_pattern = self.lexeme

        self._non_terminal_meta = {}

    def copy(self):
        return self.__class__(text=self.lexeme, line=Line(text=self.line.text, line_index=self.line.line_index))

    @classmethod
    def string_matches_pattern(cls, string, pattern):
        """Check if a given pattern that was returned by `get_patterns` matches a string."""
        return string.startswith(pattern)

    @classmethod
    def get_matching_pattern(cls, string: str):
        """Returns the pattern that matches a string. If there is none, it returns None."""
        if string is None:
            return None

        for pattern in cls.get_patterns():
            if cls.string_matches_pattern(string, pattern):
                return pattern
        return None

    @classmethod
    def reduce_to_lexeme(cls, string: str):
        """Given a string, this will return everything of it that belongs to this token."""
        return cls.get_matching_pattern(string) or ''

    @classmethod
    def string_contains_matching_pattern(cls, string: str):
        """Checks if a given string contains this token."""
        return bool(cls.get_matching_pattern(string))

    @classmethod
    def get_patterns(cls):
        """Returns all the patterns that identify a token."""
        raise NotImplementedError()

    def get_meta_data_for_sequence(self, sequence):
        return {}

    @property
    def non_terminal_meta(self):
        return self._non_terminal_meta

    def set_non_terminal_meta_value(self, key, value):
        self._non_terminal_meta[key] = value

    def __repr__(self):
        return '{}: "{}" in {} (pattern: {})'.format(
            self.__class__.__name__, self.lexeme, self.line, self.matched_pattern)

    def __str__(self):
        return self.lexeme or ''
