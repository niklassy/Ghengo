from typing import Optional

from gherkin.config import GHERKIN_CONFIG
from gherkin.line import GherkinLine
from settings import Settings


class KeywordPrototype(object):
    """Used in combination with lines to indicate which keyword is in a line."""
    def __init__(self, starting_line, prototype_of):
        self.starting_line = starting_line
        self.prototype_of = prototype_of

    def transform_to_keyword(self, end_line):
        return self.prototype_of(self.starting_line, end_line)


class Keyword(object):
    id = None
    keyword_with_colon = False

    def __init__(self, parent, lines):
        self.parent = parent
        self.lines = lines

    @classmethod
    def termination_keywords(cls):
        return []

    @classmethod
    def prototype(cls, starting_line):
        return KeywordPrototype(starting_line=starting_line, prototype_of=cls)

    @classmethod
    def get_keywords(cls):
        return GHERKIN_CONFIG[Settings.language][cls.id]

    @classmethod
    def get_match_in_line(cls, line: GherkinLine) -> Optional[str]:
        for keyword in cls.get_keywords():
            if line.starts_with_string(keyword, has_colon=cls.keyword_with_colon):
                return keyword
        return None

    @classmethod
    def exists_in_line(cls, line: GherkinLine) -> bool:
        return bool(cls.get_match_in_line(line))
