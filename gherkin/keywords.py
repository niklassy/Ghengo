from gherkin.config import GHERKIN_CONFIG
from gherkin.line import GherkinLine
from settings import Settings


class GherkinKeyword(object):
    children = []
    comments = []
    tags = []

    parent = None
    keyword = None
    keyword_with_column = False

    def __init__(self, parent, comments=None):
        self.parent = parent
        self.children = []
        self.tags = []
        self.comments = comments if comments is not None else []

    def set_tags(self, tags):
        self.tags = tags

    def set_children(self, children):
        self.children = children

    @classmethod
    def get_keywords(cls):
        return GHERKIN_CONFIG[Settings.language][cls.keyword]

    @classmethod
    def line_matches_keyword(cls, line: GherkinLine):
        if cls.keyword_with_column:
            return any([line.starts_with_column_keyword(keyword) for keyword in cls.get_keywords()])

        return any([line.starts_with_string(keyword) for keyword in cls.get_keywords()])


class Feature(GherkinKeyword):
    keyword_with_column = True
    keyword = 'feature'


class SpecialCharacterKeyword(GherkinKeyword):
    def __init__(self, parent):
        super().__init__(parent=parent)

    @classmethod
    def get_keywords(cls):
        return cls.keyword


class Tag(SpecialCharacterKeyword):
    keyword = '@'

    def __init__(self, parent, name):
        super().__init__(parent)
        self.name = name
