from typing import Optional

from gherkin.document import GherkinDocument
from gherkin.exception import InvalidGherkin
from gherkin.keywords import Feature, Tag, Rule, Scenario, GherkinDescription, GherkinKeyword, Comment, \
    Given, But, Background, Then, And, When
from gherkin.line import GherkinLine
from settings import Settings


class GherkinKeywordOutline(object):
    pass


class Compiler(object):
    _keywords = [
        Tag,
        Comment,
        Feature,
        Rule,
        Background,
        Scenario,
        Given,
        When,
        Then,
        And,
        But,
    ]

    def __init__(self, gherkin_doc_string):
        # TODO: support file parsing
        self.gherkin_doc_string: str = gherkin_doc_string

    def compile(self):
        return self._compile_gherkin_doc()

    def _compile_gherkin_doc(self):
        lines = [GherkinLine(text, index) for index, text in enumerate(self.gherkin_doc_string.splitlines())]
        self.gherkin_doc = GherkinDocument(lines)

        for line in self.gherkin_doc.lines:
            if Feature.line_matches_keyword(line):
                feature = self._create_feature(self.gherkin_doc, line)
                self.gherkin_doc.add_feature(feature)
                self._compile_keyword(feature, line)

        if self.gherkin_doc.feature is None:
            raise InvalidGherkin('There must be a feature in a feature file.')

        return self.gherkin_doc

    def _compile_keyword(self, keyword: GherkinKeyword, start_line: GherkinLine):
        # handle tags if needed
        if keyword.may_have_tags:
            try:
                previous_line = self.gherkin_doc.get_previous_line(start_line)
            except IndexError:
                previous_line = None

            keyword_has_tags = Tag.line_matches_keyword(previous_line)
            if keyword_has_tags:
                tags = self._compile_tags(start_line=previous_line, parent=keyword)
                keyword.set_tags(tags)

        # TODO: handle description (e.g. for feature)
        # save how far the document has been compiled, since recursion calls will be ahead of this loop
        compiled_until_line_index = start_line.line_index

        for line in self.gherkin_doc.get_lines_after(start_line):
            # if a recursion call has already processed this line, skip it
            if not line or line.line_index <= compiled_until_line_index:
                continue

            # check if there are any matches with a valid child for current keyword
            # search for a keyword
            found_keyword: Optional[GherkinKeyword] = None
            for _existing_keyword_cls in self._keywords:
                if _existing_keyword_cls.line_matches_keyword(line):
                    found_keyword = _existing_keyword_cls
                    continue

            # if no, skip
            if found_keyword is None:
                continue

            # if another keyword of the same type was found, we are done with this keyword
            # we are also done if there is another keyword that is a valid sibling of this keyword
            if keyword.ends_at_keyword(found_keyword):
                keyword.end_line = self.gherkin_doc.get_previous_line(line)
                break

            # if another keyword is found, create it
            obj = self._create_keyword(found_keyword, keyword, line)

            # compile it afterwards via recursion and add it to this keyword
            child_keyword_obj = self._compile_keyword(obj, line)
            keyword.add_child(child_keyword_obj)

            # finally save how far the child keyword has covered
            compiled_until_line_index = child_keyword_obj.end_line.line_index

        if keyword.end_line is None:
            keyword.end_line = self.gherkin_doc.lines[-1]

        return keyword

    def _create_keyword(self, keyword_cls, parent, start_line):
        return keyword_cls(parent=parent, start_line=start_line)

    def _create_feature(self, parent, start_line):
        return Feature(parent=parent, start_line=start_line)

    def _create_comment(self, parent, start_line):
        return Comment(parent=parent, start_line=start_line)

    def _create_scenario(self, parent, start_line):
        return Scenario(parent=parent, start_line=start_line)

    def _create_rule(self, parent, start_line):
        return Rule(parent=parent, start_line=start_line)

    def _compile_tags(self, parent: GherkinKeyword, start_line: GherkinLine) -> [Tag]:
        tags = []
        tag_texts = start_line.trimmed_text.split(' ')

        for _ in tag_texts:
            tags.append(
                Tag(start_line=start_line, parent=parent)
            )

        return tags
