from typing import Optional

from gherkin.config import GHERKIN_CONFIG
from gherkin.compiler.line import GherkinLine
from settings import Settings


class Token(object):
    """
    A token represents a collection of characters in a text. If will be used later by the parser to check the
    validity. In our case, tokens are lines because Gherkin only has one `statement` per line.
    """
    # the id of token within the languages.json
    _json_id = None

    # does the keyword have a `:` at the end?
    keyword_with_colon = False

    def __init__(self, text: Optional[str], line: Optional[GherkinLine]):
        self.line: Optional[GherkinLine] = line

        self.text: Optional[str] = text
        self.matched_keyword_full = self.get_full_matching_text(text)

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
    def get_full_matching_text(cls, string: str):
        """Returns the full matching text. Everything that is returned here will be added to the token."""
        return cls.get_matching_keyword(string)

    @classmethod
    def string_fits_token(cls, string: str):
        """By default a token is recognized by a keyword that is used at the beginning of a string."""
        return bool(cls.get_matching_keyword(string))

    @classmethod
    def get_keywords(cls):
        """Returns all the keywords that identify a token."""
        try:
            keywords = GHERKIN_CONFIG[Settings.language][cls._json_id]

            if cls.keyword_with_colon:
                return ['{}:'.format(k) for k in keywords]

            return keywords
        except KeyError:
            return []

    def __repr__(self):
        return '{}-Token: "{}" in {}'.format(self.__class__.__name__, self.matched_keyword_full, self.line)


class Feature(Token):
    _json_id = 'feature'
    keyword_with_colon = True


class Rule(Token):
    _json_id = 'rule'
    keyword_with_colon = True


class Scenario(Token):
    _json_id = 'scenario'
    keyword_with_colon = True


class ScenarioOutline(Token):
    _json_id = 'scenarioOutline'
    keyword_with_colon = True


class Examples(Token):
    _json_id = 'examples'
    keyword_with_colon = True


class DataTable(Token):
    @classmethod
    def get_keywords(cls):
        return ['|']

    @classmethod
    def get_full_matching_text(cls, string: str):
        return string

    @classmethod
    def string_fits_token(cls, string: str):
        keyword = cls.get_keywords()[0]
        clean_string = string.rstrip().lstrip()
        return clean_string and clean_string[0] == keyword and clean_string[-1] == keyword


class DocString(Token):
    @classmethod
    def get_keywords(cls):
        return ['"""', '```']

    @classmethod
    def get_full_matching_text(cls, string: str):
        return string


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
    def __init__(self, text, line):
        super().__init__(text, line)
        self.text = self.text.replace('#', '', 1).lstrip()

    @classmethod
    def get_keywords(cls):
        return ['#']

    @classmethod
    def get_full_matching_text(cls, string: str):
        return string


class Language(Token):
    def __init__(self, line, text):
        self.locale = self.get_locale_from_line(line.trimmed_text)
        super().__init__(line=line, text=self.locale)

    @classmethod
    def get_keywords(cls):
        return ['#']

    @classmethod
    def get_full_matching_text(cls, string: str):
        return string

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
    def get_keywords(cls):
        return ['Any string with no keywords']

    @classmethod
    def string_fits_token(cls, string: str) -> bool:
        return True


class EndOfBase(Token):
    @classmethod
    def get_matching_keyword(cls, string: str):
        return ''

    @classmethod
    def get_full_matching_text(cls, string: str):
        return ''


class EndOfLine(Token):
    def __init__(self, line: Optional[GherkinLine], *args, **kwargs):
        super().__init__(text=None, line=line)

    @classmethod
    def string_fits_token(cls, string: str):
        return False

    @classmethod
    def get_keywords(cls):
        return ['End of line']

    @classmethod
    def get_matching_keyword(cls, string: str):
        return ''

    @classmethod
    def get_full_matching_text(cls, string: str):
        return 'End of line'


class EOF(Token):
    def __init__(self, line, *args, **kwargs):
        super().__init__(text=None, line=line)

    @classmethod
    def get_matching_keyword(cls, string: str):
        return ''

    @classmethod
    def get_full_matching_text(cls, string: str):
        return 'End of file'

    @classmethod
    def get_keywords(cls):
        return ['End of file']

    @classmethod
    def string_fits_token(cls, string: str):
        return False
