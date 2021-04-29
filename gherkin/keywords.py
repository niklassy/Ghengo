from typing import Optional

from gherkin.config import GHERKIN_CONFIG
from gherkin.exception import InvalidGherkin
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
    may_have_tags = True

    valid_children: ['GherkinKeyword'] = []

    def __init__(self, parent, start_line, end_line=None):
        self.matched_keyword = self.get_keyword_match(start_line)
        self.name = start_line.get_text_after_keyword(self.get_keyword_match(start_line), has_column=self.keyword_with_colon)
        self.parent = parent
        self.start_line = start_line
        self.end_line = end_line

        if self.may_have_children:
            self.children = []
            self.tags = []

        if self.may_have_comments:
            self.comments = []

    @property
    def may_have_children(self):
        return len(self.valid_children) > 0

    @property
    def may_have_comments(self):
        return Comment in self.valid_children

    def _validate_tags(self, tags: ['Tag']):
        for tag in tags:
            if tag.start_line.line_index != self.start_line.line_index - 1:
                raise InvalidGherkin('Tags must be in the line before {}'.format(self.__class__.__name__))

    def set_tags(self, tags: ['Tag']):
        if self.may_have_tags:
            self._validate_tags(tags)
            self.tags = tags

    def _validate_child(self, child: 'GherkinKeyword'):
        if child.__class__ not in self.valid_children:
            raise InvalidGherkin('Not valid child')

    def add_child(self, child: 'GherkinKeyword'):
        if self.may_have_children:
            self._validate_child(child)
            self.children.append(child)

    def has_child_of_cls(self, cls):
        return any([child.__class__ == cls for child in self.children])

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


class Scenario(GherkinKeyword):
    keyword = 'scenario'
    keyword_with_colon = True


class Rule(GherkinKeyword):
    keyword = 'rule'
    keyword_with_colon = True
    valid_children = [Scenario]


# Keywords for special characters

class SpecialCharacterKeyword(GherkinKeyword):
    may_have_tags = False

    def __init__(self, start_line, parent, end_line=None):
        if end_line is None:
            end_line = start_line

        super().__init__(start_line=start_line, end_line=end_line, parent=parent)

    @classmethod
    def get_keywords(cls):
        return cls.keyword


class Tag(SpecialCharacterKeyword):
    keyword = '@'


class Comment(SpecialCharacterKeyword):
    keyword = '#'

    def __init__(self, start_line, parent, end_line=None):
        super().__init__(start_line=start_line, end_line=end_line, parent=parent)
        self.text = start_line.trimmed_text.replace(self.keyword, '').lstrip()


class Feature(GherkinKeyword):
    keyword_with_colon = True
    keyword = 'feature'
    valid_children = [Comment, Rule, Scenario]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.text: Optional[GherkinText] = None

    def _validate_child(self, child: 'GherkinKeyword'):
        super()._validate_child(child)

        if child.__class__ == Rule and self.has_child_of_cls(Scenario) or \
                child.__class__ == Scenario and self.has_child_of_cls(Rule):
            raise InvalidGherkin('A feature cannot have Rules and Scenarios as children.')

    def set_text(self, text: GherkinText):
        self.text = text
