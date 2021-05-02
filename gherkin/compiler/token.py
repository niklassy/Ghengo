from typing import Optional, Union, Tuple

from gherkin.config import GHERKIN_CONFIG
from gherkin.compiler.line import GherkinLine
from settings import Settings


class Token(object):
    """
    A token represents a collection of characters in a text. If will be used later by the parser to check the
    validity. In our case, tokens are lines because Gherkin only has one `statement` per line.
    """
    _json_id = None
    keyword_with_colon = False

    def __init__(self, text: Optional[str], line: Optional[GherkinLine]):
        self.line: Optional[GherkinLine] = line
        self._matched_keyword = None

        self.text: Optional[str] = text
        self.matched_keyword_full = self.get_full_matching_text(text)

    @classmethod
    def get_matching_keyword(cls, string: str):
        for keyword in cls.get_keywords():
            if string.startswith(keyword):
                return keyword
        return None

    @classmethod
    def get_full_matching_text(cls, string: str):
        return '{}{}'.format(cls.get_matching_keyword(string) or '', ':' if cls.keyword_with_colon else '')

    @classmethod
    def string_fits_token(cls, string: str):
        """By default a token is recognized by a keyword that is used at the beginning of a string."""
        return bool(cls.get_matching_keyword(string))

    @classmethod
    def get_keywords(cls):
        try:
            return GHERKIN_CONFIG[Settings.language][cls._json_id]
        except KeyError:
            return []


class Feature(Token):
    _json_id = 'feature'
    keyword_with_colon = True


class Rule(Token):
    _json_id = 'rule'
    keyword_with_colon = True


class Scenario(Token):
    _json_id = 'scenario'
    keyword_with_colon = True


class Background(Token):
    _json_id = 'background'
    keyword_with_colon = True


class Given(Token):
    _json_id = 'given'


class When(Token):
    _json_id = 'when'


class Then(Token):
    _json_id = 'then'


class And(Token):
    _json_id = 'and'


class But(Token):
    _json_id = 'but'


class Tag(Token):
    def __init__(self, text, line):
        super().__init__(line=line, text=text)
        self.text = text
        self.full_text = '@{}'.format(text)

    def get_full_matching_text(self, string: str):
        return '@{}'.format(self.text)

    @classmethod
    def get_keywords(cls):
        return ['@']

    def get_matching_keyword(self, string: str):
        return super().get_matching_keyword(string)


class Tags(Token):
    def __new__(cls, text, line):
        return [Tag(line=line, text=text.replace('@', '')) for text in line.trimmed_text.split(' ')]

    @classmethod
    def get_keywords(cls):
        return ['@']

    @classmethod
    def get_full_matching_text(cls, string: str):
        return string


class Comment(Token):
    @classmethod
    def get_keywords(cls):
        return ['#']

    @classmethod
    def get_full_matching_text(cls, string: str):
        return string


class Language(Comment):
    def __init__(self, line, text):
        self.locale = self.get_locale_from_line(line.trimmed_text)
        super().__init__(line=line, text=self.locale)

    @classmethod
    def string_fits_token(cls, string: str):
        locale = cls.get_locale_from_line(string)
        return super().string_fits_token(string) and locale in GHERKIN_CONFIG

    @classmethod
    def get_locale_from_line(cls, string):
        return string.replace(' ', '').replace('#language', '')


class Empty(Token):
    @classmethod
    def get_matching_keyword(cls, string: str):
        return ''

    @classmethod
    def string_fits_token(cls, string: str):
        return not bool(string)


class Description(Token):
    @classmethod
    def get_matching_keyword(cls, string: str):
        return string

    @classmethod
    def string_fits_token(cls, string: str) -> bool:
        # TODO: check that no other token matched
        return super().string_fits_token(string)


class EndOfBase(Token):
    @classmethod
    def get_matching_keyword(cls, string: str):
        return ''

    @classmethod
    def get_full_matching_text(cls, string: str):
        return ''


class EndOfLine(Token):
    def __init__(self, line: GherkinLine, *args, **kwargs):
        super().__init__(text=None, line=line)


class EOF(Token):
    def __init__(self, line, *args, **kwargs):
        super().__init__(text=None, line=line)
