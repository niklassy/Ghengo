class Line(object):
    """Represents a line in a gherkin document."""
    def __init__(self, text, line_index):
        self.text = text
        self.line_index = line_index
        self.trimmed_text = text.lstrip()
        self.intend = len(self.text) - len(self.trimmed_text)

    def is_empty(self):
        return len(self.trimmed_text) > 0

    def __bool__(self):
        return self.is_empty()

    def __str__(self):
        return '`{}` (Line {})'.format(self.trimmed_text, self.line_index)

    def __repr__(self):
        return str(self)


