import re
from typing import Optional

from gherkin.compiler_base.token import Token
from gherkin.config import GHERKIN_CONFIG
from gherkin.compiler_base.line import Line
from gherkin.settings import Settings


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
        return string if cls.string_contains_token(string) else ''


class FeatureToken(GherkinToken):
    _json_id = 'feature'
    keyword_with_colon = True


class RuleToken(GherkinToken):
    _json_id = 'rule'
    keyword_with_colon = True


class ScenarioToken(GherkinToken):
    _json_id = 'scenario'
    keyword_with_colon = True


class ScenarioOutlineToken(GherkinToken):
    _json_id = 'scenarioOutline'
    keyword_with_colon = True


class ExamplesToken(GherkinToken):
    _json_id = 'examples'
    keyword_with_colon = True


class DataTableToken(TokenContainsWholeLineMixin, GherkinToken):
    @classmethod
    def get_keywords(cls):
        return ['|']

    @classmethod
    def string_contains_token(cls, string: str):
        keyword = cls.get_keywords()[0]
        clean_string = string.rstrip().lstrip()
        return clean_string and clean_string[0] == keyword and clean_string[-1] == keyword


class DocStringToken(TokenContainsWholeLineMixin, GherkinToken):
    @classmethod
    def get_keywords(cls):
        return ['"""', '```']


class BackgroundToken(GherkinToken):
    _json_id = 'background'
    keyword_with_colon = True


class GivenToken(GherkinToken):
    _json_id = 'given'


class WhenToken(GherkinToken):
    _json_id = 'when'


class ThenToken(GherkinToken):
    _json_id = 'then'


class AndToken(GherkinToken):
    _json_id = 'and'


class ButToken(GherkinToken):
    _json_id = 'but'


class TagToken(TokenContainsWholeLineMixin, GherkinToken):
    REG_EX = '@[a-zA-Z0-9_.-]+'

    @classmethod
    def get_keywords(cls):
        return ['@']

    @classmethod
    def string_matches_keyword(cls, string, keyword):
        return bool(re.match('^{tag_pattern}$'.format(tag_pattern=cls.REG_EX), string))


class TagsToken(TokenContainsWholeLineMixin, GherkinToken):
    def __new__(cls, text, line):
        output = []

        for tag_element_str in line.trimmed_text.split(' '):
            if TagToken.string_contains_token(tag_element_str):
                token = TagToken(line=line, text=tag_element_str)
            else:
                token = DescriptionToken(line=line, text=tag_element_str)

            output.append(token)

        return output

    @classmethod
    def string_matches_keyword(cls, string: str, keyword):
        return bool(re.match('^{tag_pattern}( {tag_pattern})*$'.format(tag_pattern=TagToken.REG_EX), string))

    @classmethod
    def get_keywords(cls):
        return ['@']


class CommentToken(TokenContainsWholeLineMixin, GherkinToken):
    @classmethod
    def get_keywords(cls):
        return ['#']


class LanguageToken(TokenContainsWholeLineMixin, GherkinToken):
    def __init__(self, text, line):
        super().__init__(line=line, text=text)
        self.locale = self.get_locale_from_line(line.trimmed_text)

    @classmethod
    def get_keywords(cls):
        return ['#']

    @classmethod
    def string_contains_token(cls, string: str):
        locale = cls.get_locale_from_line(string)
        return super().string_contains_token(string) and bool(locale) and locale in GHERKIN_CONFIG

    @classmethod
    def get_locale_from_line(cls, string):
        no_left_spaces = string.replace('#', '', 1).lstrip()
        if not no_left_spaces.startswith('language:'):
            return ''

        no_language = no_left_spaces.replace('language:', '', 1)
        if len(no_language) == 0 or no_language[0] != ' ':
            return ''

        return no_language.replace(' ', '')


class EmptyToken(TokenContainsWholeLineMixin, GherkinToken):
    @classmethod
    def get_matching_keyword(cls, string: str):
        return ''

    @classmethod
    def string_contains_token(cls, string: str):
        return not bool(string.replace(' ', ''))


class DescriptionToken(TokenContainsWholeLineMixin, GherkinToken):
    @classmethod
    def get_keywords(cls):
        return ['Any string with no keywords']

    @classmethod
    def string_contains_token(cls, string: str) -> bool:
        return True


class EndOfLineToken(GherkinToken):
    def __init__(self, line: Optional[Line], *args, **kwargs):
        super().__init__(text=None, line=line)

    @classmethod
    def string_contains_token(cls, string: str):
        return False

    @classmethod
    def get_keywords(cls):
        return ['End of line']


class EOFToken(GherkinToken):
    def __init__(self, line, *args, **kwargs):
        super().__init__(text=None, line=line)

    @classmethod
    def get_keywords(cls):
        return ['End of file']

    @classmethod
    def string_contains_token(cls, string: str):
        return False
