from typing import Optional

from gherkin.config import GHERKIN_CONFIG
from gherkin.exception import InvalidGherkin
from gherkin.line import GherkinLine
from settings import Settings


class GherkinDescription(object):
    def __init__(self, line: GherkinLine):
        self.line: GherkinLine = line

    @property
    def text(self) -> str:
        return self.line.trimmed_text


class GherkinKeyword(object):
    parent = None
    id = None
    keyword_with_colon = False
    may_have_tags = True
    may_have_description = True

    valid_children: ['GherkinKeyword'] = []

    def __init__(self, parent, start_line, end_line=None):
        self.matched_keyword = self.get_keyword_match(start_line)
        self.name = start_line.get_text_after_keyword(
            self.get_keyword_match(start_line), has_column=self.keyword_with_colon)
        self.parent = parent
        self.start_line = start_line
        self.end_line = end_line

        if self.may_have_children:
            self.children: ['GherkinKeyword'] = []
            self.tags = []

        if self.may_have_comments:
            self.comments = []

        if self.may_have_description:
            self.descriptions = []

    def __str__(self):
        base = '{} ("{}")'.format(self.__class__.__name__, self.name)
        if self.may_have_children:
            base += ' || {}'.format(self.children)
        return base

    def __repr__(self):
        return str(self)

    @classmethod
    def get_valid_siblings(cls) -> ['GherkinKeyword']:
        return []

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

    def ends_at_keyword(self, keyword_cls):
        """Does this keyword end the given keyword?"""
        sibling_exists = keyword_cls in self.get_valid_siblings()
        return keyword_cls == self.__class__ or sibling_exists

    def validate_child(self, child: 'GherkinKeyword'):
        if child.__class__ not in self.valid_children:
            raise InvalidGherkin('Not valid child')

    def validate_sibling(self, sibling: 'GherkinKeyword'):
        if sibling.__class__ not in self.get_valid_siblings():
            raise InvalidGherkin('Not valid sibling')

    def add_child(self, child: 'GherkinKeyword'):
        if isinstance(child, Comment):
            if not self.may_have_comments:
                raise InvalidGherkin('Keyword cant have a comment.')

            self.comments.append(child)
            return

        if self.may_have_children:
            self.validate_child(child)

            for existing_child in self.children:
                existing_child.validate_sibling(child)

            self.children.append(child)

    def has_child_of_cls(self, cls):
        return any([child.__class__ == cls for child in self.children])

    def set_comments(self, comments: ['Comment']):
        # TODO: remove
        if self.may_have_comments:
            self.comments = comments

    @classmethod
    def get_keywords(cls):
        return GHERKIN_CONFIG[Settings.language][cls.id]

    @classmethod
    def get_keyword_match(cls, line: GherkinLine) -> Optional[str]:
        for keyword in cls.get_keywords():
            if line.starts_with_string(keyword, has_colon=cls.keyword_with_colon):
                return keyword
        return None

    @classmethod
    def line_matches_keyword(cls, line: GherkinLine) -> bool:
        return bool(cls.get_keyword_match(line))


class ContinuedStep(GherkinKeyword):
    may_have_tags = False

    @classmethod
    def get_valid_siblings(cls) -> ['GherkinKeyword']:
        return [But, And]

    def ends_at_keyword(self, keyword_cls):
        output = super().ends_at_keyword(keyword_cls)

        return output or keyword_cls in (Given, When, Then)


class But(ContinuedStep):
    id = 'but'


class And(ContinuedStep):
    id = 'and'


class Step(GherkinKeyword):
    may_have_tags = False
    valid_children = [But, And]

    @classmethod
    def get_valid_siblings(cls) -> ['GherkinKeyword']:
        return [Given, When, Then]


class Given(Step):
    id = 'given'


class When(Step):
    id = 'when'


class Then(Step):
    id = 'then'


class Background(GherkinKeyword):
    keyword_with_colon = True
    id = 'background'

    @classmethod
    def get_valid_siblings(cls) -> ['GherkinKeyword']:
        return [Scenario]


class Scenario(GherkinKeyword):
    id = 'scenario'
    keyword_with_colon = True
    valid_children = [Given, When, Then]

    @classmethod
    def get_valid_siblings(cls) -> ['GherkinKeyword']:
        return [Scenario]

    def validate_child(self, child: 'GherkinKeyword'):
        super().validate_child(child)

        if isinstance(child, When) and not isinstance(self.children[-1], Given):
            raise InvalidGherkin('Before a `When` should come a `Given`.')

        if isinstance(child, Then) and not isinstance(self.children[-1], When):
            raise InvalidGherkin('Before a `Then` should come a `When`.')


class Rule(GherkinKeyword):
    id = 'rule'
    keyword_with_colon = True
    valid_children = [Scenario, Background]


# Keywords for special characters

class SpecialCharacterKeyword(GherkinKeyword):
    may_have_tags = False
    may_have_description = False

    def __init__(self, start_line, parent, end_line=None):
        if end_line is None:
            end_line = start_line

        super().__init__(start_line=start_line, end_line=end_line, parent=parent)

    @classmethod
    def get_keywords(cls):
        return cls.id


class Tag(SpecialCharacterKeyword):
    # TODO: not split up correctly
    id = '@'


class Comment(SpecialCharacterKeyword):
    id = '#'

    def __init__(self, start_line, parent, end_line=None):
        super().__init__(start_line=start_line, end_line=end_line, parent=parent)
        self.text = start_line.trimmed_text.replace(self.name, '').lstrip()


class Feature(GherkinKeyword):
    keyword_with_colon = True
    id = 'feature'
    valid_children = [Comment, Rule, Scenario]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.text: Optional[GherkinDescription] = None

    def validate_child(self, child: 'GherkinKeyword'):
        super().validate_child(child)

        if child.__class__ == Rule and self.has_child_of_cls(Scenario) or \
                child.__class__ == Scenario and self.has_child_of_cls(Rule):
            raise InvalidGherkin('A feature cannot have Rules and Scenarios as children.')

    def set_text(self, text: GherkinDescription):
        self.text = text
