from gherkin.keywords import Feature
from gherkin.line import GherkinLine


class GherkinDocument(object):
    def __init__(self, lines: [GherkinLine]):
        self.lines = sorted(lines.copy(), key=lambda line: line.line_index)
        self.feature = None

    def get_next_line(self, line: GherkinLine) -> GherkinLine:
        return self.lines[line.line_index + 1]

    def get_previous_line(self, line: GherkinLine) -> GherkinLine:
        return self.lines[line.line_index - 1]

    def add_feature(self, feature: Feature):
        self.feature = feature
