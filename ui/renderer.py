from gherkin.compiler import GherkinToPyTestCompiler
from gherkin.token import EndOfLineToken
from gherkin.utils import get_suggested_intend_after_line


class GherkinEditorRenderer(object):
    def __init__(self, window, editor):
        self.window = window
        self.editor = editor
        self.editor_widget = editor.Widget
        self.compiler = GherkinToPyTestCompiler()

    def get_cursor_position(self):
        return self.editor_widget.index('insert').split('.')

    def update_text(self, text):
        tokens = self.compiler.use_lexer(text)

        editor_widget = self.editor_widget
        cursor_y, cursor_x = self.get_cursor_position()
        self.editor.update('')

        for i, token in enumerate(tokens):
            if i >= len(tokens) - 2:
                continue

            try:
                previous_token = tokens[i - 1]
            except IndexError:
                previous_token = None

            # intend
            if previous_token and isinstance(previous_token, EndOfLineToken):
                indent_str = get_suggested_intend_after_line(tokens, token.line.line_index - 1)
                self.editor.update(indent_str, append=True)
                cursor_x = int(cursor_x) + len(indent_str)

            color = token.get_meta_data_for_sequence(tokens).get('color')
            self.editor.update(str(token), text_color_for_value=color, append=True)

        editor_widget.mark_set("insert", "%d.%d" % (float(cursor_y), float(cursor_x)))
