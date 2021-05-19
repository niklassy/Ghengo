from typing import Optional

from gherkin.compiler_base.token import Token
from gherkin.config import GHERKIN_CONFIG
from gherkin.compiler_base.line import Line
from settings import Settings


class GherkinToken(Token):
    _json_id = None
    
    @classmethod
    def get_keywords(cls):
        try:
            keywords = GHERKIN_CONFIG[Settings.language][cls._json_id]

            if cls.keyword_with_colon:
                return ['{}:'.format(k) for k in keywords]

            return keywords
        except KeyError:
            return []


class TokenContainsWholeLineMixin(object):
    @classmethod
    def reduce_to_belonging(cls, string: str):
        return string


class Feature(GherkinToken):
    _json_id = 'feature'
    keyword_with_colon = True


class Rule(GherkinToken):
    _json_id = 'rule'
    keyword_with_colon = True


class Scenario(GherkinToken):
    _json_id = 'scenario'
    keyword_with_colon = True


class ScenarioOutline(GherkinToken):
    _json_id = 'scenarioOutline'
    keyword_with_colon = True


class Examples(GherkinToken):
    _json_id = 'examples'
    keyword_with_colon = True


class DataTable(TokenContainsWholeLineMixin, GherkinToken):
    @classmethod
    def get_keywords(cls):
        return ['|']

    @classmethod
    def string_contains_token(cls, string: str):
        keyword = cls.get_keywords()[0]
        clean_string = string.rstrip().lstrip()
        return clean_string and clean_string[0] == keyword and clean_string[-1] == keyword


class DocString(TokenContainsWholeLineMixin, GherkinToken):
    @classmethod
    def get_keywords(cls):
        return ['"""', '```']


class Background(GherkinToken):
    _json_id = 'background'
    keyword_with_colon = True


class Given(GherkinToken):
    _json_id = 'given'


class When(GherkinToken):
    _json_id = 'when'


class Then(GherkinToken):
    _json_id = 'then'


class And(GherkinToken):
    _json_id = 'and'


class But(GherkinToken):
    _json_id = 'but'


class Tag(GherkinToken):
    def __init__(self, text, line):
        super().__init__(line=line, text=text)
        self.text = text
        self.full_text = '@{}'.format(text)

    def reduce_to_belonging(self, string: str):
        return '@{}'.format(self.text)

    @classmethod
    def get_keywords(cls):
        return ['@']

    def get_matching_keyword(self, string: str):
        return super().get_matching_keyword(string)


class Tags(TokenContainsWholeLineMixin, GherkinToken):
    def __new__(cls, text, line):
        return [Tag(line=line, text=text.replace('@', '')) for text in line.trimmed_text.split(' ')]

    @classmethod
    def get_keywords(cls):
        return ['@']


class Comment(TokenContainsWholeLineMixin, GherkinToken):
    def __init__(self, text, line):
        super().__init__(text, line)

        if self.text is not None:
            self.text = self.text.replace('#', '', 1).lstrip()

    @classmethod
    def get_keywords(cls):
        return ['#']


class Language(TokenContainsWholeLineMixin, GherkinToken):
    def __init__(self, line, text):
        self.locale = self.get_locale_from_line(line.trimmed_text)
        super().__init__(line=line, text=self.locale)

    @classmethod
    def get_keywords(cls):
        return ['#']

    @classmethod
    def string_contains_token(cls, string: str):
        locale = cls.get_locale_from_line(string)
        return super().string_contains_token(string) and locale in GHERKIN_CONFIG

    @classmethod
    def get_locale_from_line(cls, string):
        return string.replace(' ', '').replace('#language', '')


class Empty(GherkinToken):
    @classmethod
    def get_matching_keyword(cls, string: str):
        return ''

    @classmethod
    def string_contains_token(cls, string: str):
        return not bool(string)


class Description(TokenContainsWholeLineMixin, GherkinToken):
    @classmethod
    def get_keywords(cls):
        return ['Any string with no keywords']

    @classmethod
    def string_contains_token(cls, string: str) -> bool:
        return True


class EndOfLine(GherkinToken):
    def __init__(self, line: Optional[Line], *args, **kwargs):
        super().__init__(text=None, line=line)

    @classmethod
    def string_contains_token(cls, string: str):
        return False

    @classmethod
    def get_keywords(cls):
        return ['End of line']


class EOF(GherkinToken):
    def __init__(self, line, *args, **kwargs):
        super().__init__(text=None, line=line)

    @classmethod
    def get_keywords(cls):
        return ['End of file']

    @classmethod
    def string_contains_token(cls, string: str):
        return False
