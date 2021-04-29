from typing import Optional

from gherkin.exception import InvalidGherkin
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
        if not self.feature:
            self.feature = feature
        else:
            raise InvalidGherkin('There can only be one feature per gherkin document.')

    def get_lines_after(self, from_line: GherkinLine, to_line: Optional[GherkinLine] = None) -> [GherkinLine]:
        if to_line is None:
            return self.lines[from_line.line_index + 1:]

        return self.lines[from_line.line_index + 1:to_line.line_index]
