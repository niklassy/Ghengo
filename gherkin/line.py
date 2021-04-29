class GherkinLine(object):
    def __init__(self, text, line_index):
        self.text = text
        self.line_index = line_index
        self.trimmed_text = text.lstrip()
        self.intend = len(self.text) - len(self.trimmed_text)

    def starts_with_string(self, string):
        return self.trimmed_text.startswith(string)

    def starts_with_column_keyword(self, keyword):
        return self.starts_with_string('{}:'.format(keyword))

    def is_empty(self):
        return bool(self)

    def __bool__(self):
        return len(self.trimmed_text) > 0

    def __str__(self):
        return 'GherkinLine (Line {}) - {}'.format(self.line_index, self.trimmed_text)


