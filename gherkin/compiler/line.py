class GherkinLine(object):
    def __init__(self, text, line_index):
        self.text = text
        self.line_index = line_index
        self.trimmed_text = text.lstrip()
        self.intend = len(self.text) - len(self.trimmed_text)

    def get_text_after_keyword(self, string, has_column=False):
        keyword = '{}:'.format(string) if has_column else string
        return self.trimmed_text.split(keyword)[1].lstrip()

    def starts_with_string(self, string, has_colon=False):
        keyword = '{}:'.format(string) if has_colon else string
        return self.trimmed_text.startswith(keyword)

    def is_empty(self):
        return bool(self)

    def __bool__(self):
        return len(self.trimmed_text) > 0

    def __str__(self):
        return 'GherkinLine (Line {}) - {}'.format(self.line_index, self.trimmed_text)


