import re
from typing import Optional

from gherkin.compiler_base.token import Token
from gherkin.config import GHERKIN_CONFIG
from gherkin.compiler_base.line import Line
from settings import Settings, GHERKIN_INDENT_SPACES


class GherkinToken(Token):
    color = None
    _json_id = None
    children_intended = False

    @classmethod
    def get_keywords(cls):
        try:
            keywords = GHERKIN_CONFIG[Settings.language][cls._json_id]

            if cls.keyword_with_colon:
                return ['{}:'.format(k) for k in keywords]

            return keywords
        except KeyError:
            return []

    def get_meta_data_for_sequence(self, sequence):
        return {'color': self.color}


class TokenContainsWholeLineMixin(object):
    @classmethod
    def reduce_to_belonging(cls, string: str):
        return string if cls.string_contains_token(string) else ''


class FeatureToken(GherkinToken):
    color = 'orange'
    _json_id = 'feature'
    keyword_with_colon = True
    children_intended = True


class RuleToken(GherkinToken):
    color = 'orange'
    _json_id = 'rule'
    keyword_with_colon = True
    children_intended = True


class ScenarioToken(GherkinToken):
    color = 'orange'
    _json_id = 'scenario'
    keyword_with_colon = True
    children_intended = True


class ScenarioOutlineToken(GherkinToken):
    color = 'orange'
    _json_id = 'scenarioOutline'
    keyword_with_colon = True
    children_intended = True


class ExamplesToken(GherkinToken):
    color = 'orange'
    _json_id = 'examples'
    keyword_with_colon = True
    children_intended = True


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
    color = '#006400'

    @classmethod
    def get_keywords(cls):
        return ['"""', '```']


class BackgroundToken(GherkinToken):
    color = 'orange'
    _json_id = 'background'
    keyword_with_colon = True
    children_intended = True


class GivenToken(GherkinToken):
    color = 'orange'
    _json_id = 'given'


class WhenToken(GherkinToken):
    color = 'orange'
    _json_id = 'when'


class ThenToken(GherkinToken):
    color = 'orange'
    _json_id = 'then'


class AndToken(GherkinToken):
    color = 'orange'
    _json_id = 'and'


class ButToken(GherkinToken):
    color = 'orange'
    _json_id = 'but'


class TagToken(TokenContainsWholeLineMixin, GherkinToken):
    color = 'yellow'
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
    color = '#444'

    @classmethod
    def get_keywords(cls):
        return ['#']


class LanguageToken(TokenContainsWholeLineMixin, GherkinToken):
    color = '#444'

    def __init__(self, text, line):
        super().__init__(line=line, text=text)
        self.locale = self.get_locale_from_line(line.trimmed_text)

    @property
    def at_valid_position(self):
        return self.line.line_index == 0

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

    def get_meta_data_for_sequence(self, sequence):
        me_entries = [(i, t) for i, t in enumerate(sequence) if t == self]

        if len(me_entries) == 0:
            return super().get_meta_data_for_sequence(sequence)

        my_index, me = me_entries[0]
        doc_strings = [(i, t) for i, t in enumerate(sequence) if isinstance(t, DocStringToken)]
        doc_string_pair_indexes = []
        for i, doc_string in enumerate(doc_strings):
            if i % 2 == 0:
                continue

            doc_string_pair_indexes.append((doc_strings[i - 1][0], doc_string[0]))

        if any([doc_start < my_index < doc_end for doc_start, doc_end in doc_string_pair_indexes]):
            color = '#006400'
        else:
            color = None

        return {'color': color}

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

    def __str__(self):
        return '\n'


class EOFToken(GherkinToken):
    def __init__(self, line, *args, **kwargs):
        super().__init__(text=None, line=line)

    @classmethod
    def get_keywords(cls):
        return ['End of file']

    @classmethod
    def string_contains_token(cls, string: str):
        return False
