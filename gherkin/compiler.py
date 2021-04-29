from gherkin.document import GherkinDocument
from gherkin.keywords import Feature, Tag, Rule, Scenario, Example, GherkinText, GherkinKeyword, Comment
from gherkin.line import GherkinLine
from settings import Settings


class InvalidGherkin(Exception):
    pass


class Compiler(object):
    def __init__(self, gherkin_doc_string):
        # TODO: support file parsing
        self.gherkin_doc_string: str = gherkin_doc_string

    def compile(self):
        return self._compile_gherkin_doc()

    def _compile_gherkin_doc(self):
        lines = [GherkinLine(text, index) for index, text in enumerate(self.gherkin_doc_string.splitlines())]
        gherkin_doc = GherkinDocument(lines)

        for line in gherkin_doc.lines:
            if Feature.line_matches_keyword(line):
                feature = self._compile_feature(Feature.get_keyword_match(line), gherkin_doc, line)
                gherkin_doc.add_feature(feature)

                # only one feature per file is possible
                break

        if gherkin_doc.feature is None:
            raise InvalidGherkin('There must be a feature in a feature file.')

        return gherkin_doc

    def _compile_feature(self, matched_keyword: str, gherkin_doc: GherkinDocument, starting_line: GherkinLine):
        feature = Feature(
            matched_keyword=matched_keyword,
            parent=gherkin_doc,
            name=starting_line.get_text_after_keyword(Feature.keyword, has_column=True)
        )

        children = []

        try:
            previous_line = gherkin_doc.get_previous_line(starting_line)
        except IndexError:
            previous_line = None

        # if a line exists before the feature, there might be tags that we want to extract
        if previous_line and Tag.line_matches_keyword(previous_line):
            tags = self._compile_tags(feature, previous_line)
            feature.set_tags(tags)

        # keep track of how far we have compiled the feature
        current_line = starting_line
        feature_text_lines: [GherkinLine] = []
        comments: [Comment] = []

        # the next lines may be comments
        for line in gherkin_doc.get_lines_after(from_line=starting_line):
            current_line: GherkinLine = line

            # if any of the children is found, stop searching for comments
            if Rule.line_matches_keyword(current_line) or \
                    Scenario.line_matches_keyword(current_line) or \
                    Example.line_matches_keyword(current_line):
                feature.set_text(GherkinText(feature_text_lines))
                feature.set_comments(comments)
                break

            # if there are any comments, add them
            if Comment.line_matches_keyword(line):
                comment = self._compile_comment(feature, current_line)
                comments.append(comment)
                continue

            # else features allow to have normal text
            if current_line:
                feature_text_lines.append(current_line)

        # search for rules
        for line in gherkin_doc.get_lines_after(from_line=current_line):
            if Rule.line_matches_keyword(line):
                rule = self._compile_rule(Rule.get_keyword_match(line), feature, line)
                children.append(rule)

        feature.set_children(children)

        return feature

    def _compile_rule(self, matched_keyword: str, feature: Feature, starting_line: GherkinLine) -> Rule:
        rule = Rule(
            parent=feature, matched_keyword=matched_keyword, name=starting_line.get_text_after_keyword(matched_keyword)
        )

        return rule

    def _compile_comment(self, parent: GherkinKeyword, starting_line: GherkinLine) -> Comment:
        return Comment(
            parent=parent,
            matched_keyword=Comment.keyword,
            name=starting_line.trimmed_text.replace(Comment.keyword, '')
        )

    def _compile_tags(self, feature: Feature, starting_line: GherkinLine) -> [Tag]:
        tags = []
        tag_texts = starting_line.trimmed_text.split(' ')

        for tag_text in tag_texts:
            tags.append(
                Tag(matched_keyword=Tag.keyword, name=tag_text.replace(Tag.keyword, ''), parent=feature)
            )

        return tags
