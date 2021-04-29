from gherkin.document import GherkinDocument
from gherkin.keywords import Feature, Tag
from gherkin.line import GherkinLine
from settings import Settings


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
                feature = self._compile_feature(gherkin_doc, line)
                gherkin_doc.add_feature(feature)

                # only one feature is possible
                break

        return gherkin_doc

    def _compile_feature(self, gherkin_doc: GherkinDocument, starting_line: GherkinLine):
        feature = Feature(parent=gherkin_doc)

        children = []
        tags = []

        try:
            previous_line = gherkin_doc.get_previous_line(starting_line)
        except IndexError:
            previous_line = None

        # if a line exists before the feature, there might be tags that we want to extract
        if previous_line and Tag.line_matches_keyword(previous_line):
            tag_texts = previous_line.trimmed_text.split(' ')

            for tag_text in tag_texts:
                tags.append(
                    Tag(name=tag_text.replace(Tag.keyword, ''), parent=feature)
                )

        feature.set_tags(tags)

        return feature
