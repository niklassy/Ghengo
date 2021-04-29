from gherkin.document import GherkinDocument
from gherkin.exception import InvalidGherkin
from gherkin.keywords import Feature, Tag, Rule, Scenario, GherkinText, GherkinKeyword, Comment
from gherkin.line import GherkinLine
from settings import Settings


class GherkinKeywordOutline(object):
    pass


class Compiler(object):
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

        # TODO: handle text (e.g. for feature)
        # save how far the document has been compiled, since recursion calls will be ahead of this loop
        compiled_until_line_index = start_line.line_index

        for line in self.gherkin_doc.get_lines_after(start_line):
            # if a recursion call has already processed this line, skip it
            if not line or line.line_index <= compiled_until_line_index:
                continue

            # check if there are any matches with a valid child for current keyword
            found_keyword = None
            for valid_child_cls in keyword.valid_children:
                if valid_child_cls.line_matches_keyword(line):
                    found_keyword = valid_child_cls

            # if no, skip
            if found_keyword is None:
                continue

            # if another keyword of the same type was found, we are done with this keyword
            if found_keyword == keyword.__class__:
                keyword.end_line = line
                break

            # if another keyword is found, create it
            compile_fn = getattr(self, '_create_{}'.format(found_keyword.__name__.lower()))
            obj = compile_fn(keyword, line)

            # compile it afterwards via recursion and add it to this keyword
            child_keyword_obj = self._compile_keyword(obj, line)
            keyword.add_child(child_keyword_obj)

            # finally save how far the child keyword has covered
            compiled_until_line_index = child_keyword_obj.end_line.line_index

        if keyword.end_line is None:
            keyword.end_line = self.gherkin_doc.lines[-1]

        return keyword

    def _create_feature(self, parent, start_line):
        return Feature(parent=parent, start_line=start_line)

    def _create_comment(self, parent, start_line):
        return Comment(parent=parent, start_line=start_line)

    def _create_scenario(self, parent, start_line):
        return Scenario(parent=parent, start_line=start_line)

    def _create_rule(self, parent, start_line):
        return Rule(parent=parent, start_line=start_line)

        # for line in self.gherkin_doc.get_lines_after(start_line, end_line):
        #     # if a child is found, the comments are not connected with the current keyword
        #     if keyword.may_have_children and any([valid_child_cls.line_matches_keyword(line) for valid_child_cls in keyword.valid_children]):
        #         break
        #
        #     # add comments to the keyword
        #     if keyword.may_have_comments and Comment.line_matches_keyword(line):
        #         self._compile_comment(keyword, line)
        #
        # # TODO: may use the line earlier from break of comments?
        # for line in self.gherkin_doc.get_lines_after(start_line, end_line):
        #     pass

    def _compile_feature(self, matched_keyword: str, gherkin_doc: GherkinDocument, starting_line: GherkinLine):
        feature = Feature(
            matched_keyword=matched_keyword,
            parent=gherkin_doc,
            name=starting_line.get_text_after_keyword(Feature.keyword, has_column=True)
        )

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
            if Rule.line_matches_keyword(current_line) or Scenario.line_matches_keyword(current_line):
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
        rules_exist = False
        for line in gherkin_doc.get_lines_after(from_line=current_line):
            if Rule.line_matches_keyword(line):
                rules_exist = True
                rule = self._compile_rule(Rule.get_keyword_match(line), feature, line)
                feature.add_child(rule)

        # if there are rules, we are done
        if rules_exist:
            return feature

        return feature

    def _compile_rule(self, matched_keyword: str, feature: Feature, starting_line: GherkinLine) -> Rule:
        rule = Rule(
            parent=feature, matched_keyword=matched_keyword, name=starting_line.get_text_after_keyword(matched_keyword)
        )

        return rule

    def _compile_comment(self, parent: GherkinKeyword, starting_line: GherkinLine) -> Comment:
        return Comment(
            parent=parent,
            start_line=starting_line,
            text=starting_line.trimmed_text.replace(Comment.keyword, '')
        )

    def _compile_tags(self, parent: GherkinKeyword, start_line: GherkinLine) -> [Tag]:
        tags = []
        tag_texts = start_line.trimmed_text.split(' ')

        for _ in tag_texts:
            tags.append(
                Tag(start_line=start_line, parent=parent)
            )

        return tags
