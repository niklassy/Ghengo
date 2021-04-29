from typing import Optional

from gherkin.config import GHERKIN_CONFIG
from gherkin.line import GherkinLine
from settings import Settings


class GherkinText(object):
    def __init__(self, lines: [GherkinLine]):
        self.lines: [GherkinLine] = lines

    @property
    def text(self) -> str:
        return ' '.join([line.trimmed_text for line in self.lines])


class GherkinKeyword(object):
    parent = None
    keyword = None
    keyword_with_colon = False
    may_have_children = True
    may_have_comments = True

    def __init__(self, matched_keyword, name, parent, comments=None):
        self.matched_keyword = matched_keyword
        self.name = name
        self.parent = parent

        if self.may_have_children:
            self.children = []
            self.tags = []

        if self.may_have_comments:
            self.comments = comments if comments is not None else []

    def set_tags(self, tags: ['Tag']):
        if self.may_have_children:
            self.tags = tags

    def set_children(self, children: ['GherkinKeyword']):
        if self.may_have_children:
            self.children = children

    def set_comments(self, comments: ['Comment']):
        if self.may_have_comments:
            self.comments = comments

    @classmethod
    def get_keywords(cls):
        return GHERKIN_CONFIG[Settings.language][cls.keyword]

    @classmethod
    def get_keyword_match(cls, line: GherkinLine) -> Optional[str]:
        for keyword in cls.get_keywords():
            if line.starts_with_string(keyword, has_colon=cls.keyword_with_colon):
                return keyword
        return None

    @classmethod
    def line_matches_keyword(cls, line: GherkinLine) -> bool:
        return bool(cls.get_keyword_match(line))


class Feature(GherkinKeyword):
    keyword_with_colon = True
    keyword = 'feature'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.text: Optional[GherkinText] = None

    def set_text(self, text: GherkinText):
        self.text = text


class Rule(GherkinKeyword):
    keyword = 'rule'
    keyword_with_colon = True


class Scenario(GherkinKeyword):
    keyword = 'scenario'
    keyword_with_colon = True


class Example(Scenario):
    pass


# Keywords for special characters

class SpecialCharacterKeyword(GherkinKeyword):
    may_have_children = False
    may_have_comments = False

    def __init__(self, matched_keyword, parent, name):
        super().__init__(matched_keyword=matched_keyword, parent=parent, name=name)

    @classmethod
    def get_keywords(cls):
        return cls.keyword


class Tag(SpecialCharacterKeyword):
    keyword = '@'


class Comment(SpecialCharacterKeyword):
    keyword = '#'

    def __init__(self, matched_keyword, parent, text: str):
        super().__init__(matched_keyword=matched_keyword, parent=parent, name='Comment from {}'.format(parent))
        self.text = text.lstrip()
