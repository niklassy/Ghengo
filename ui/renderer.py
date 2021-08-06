from gherkin.compiler import GherkinToPyTestCompiler
from gherkin.token import EndOfLineToken
from gherkin.utils import get_suggested_intend_after_line
from ui.window import WindowValues


class GherkinEditorRenderer(object):
    def __init__(self, window, editor):
        self.window = window
        self.editor = editor
        self.editor_widget = editor.Widget
        self.compiler = GherkinToPyTestCompiler()

        self.editor_widget.bind('<Tab>', self.on_forward_tab)
        self.editor_widget.bind('<Shift-Tab>', self.on_backwards_tab)

        self._cursor_x = 0
        self._cursor_y = 0

    def get_editor_value(self):
        return WindowValues.get_values()[self.editor.Key]

    def on_forward_tab(self, *args):
        full_text = self.get_editor_value()
        lines = full_text.split('\n') if full_text != '\n' else ['']
        new_lines = []

        cursor_y, cursor_x = self.get_cursor_position()
        new_cursor_x = int(cursor_x)

        for i, line in enumerate(lines):
            if i == int(cursor_y) - 1:
                line = line[:int(cursor_x)] + '  ' + line[int(cursor_x):]
                new_cursor_x += 2

            new_lines.append(line)

        self.update_text('\n'.join(new_lines))
        self.set_cursor_position(x=new_cursor_x, y=cursor_y)
        return 'break'

    def on_backwards_tab(self, *args):
        full_text = self.get_editor_value()
        lines = full_text.split('\n') if full_text != '\n' else ['']
        new_lines = []

        cursor_y, cursor_x = self.get_cursor_position()
        new_cursor_x = int(cursor_x)

        for i, line in enumerate(lines):
            if i == int(cursor_y) - 1 and len(line) > 0 and line[0] == ' ':
                new_start_index = 1
                new_cursor_x -= 1

                if line[1] == ' ':
                    new_start_index = 2
                    new_cursor_x -= 1
                line = line[new_start_index:]

            new_lines.append(line)

        self.update_text('\n'.join(new_lines))
        self.set_cursor_position(y=cursor_y, x=new_cursor_x)

        return 'break'

    def set_cursor_position(self, x, y):
        self.editor_widget.mark_set("insert", "%d.%d" % (float(y), float(x)))

    def get_cursor_position(self):
        return self.editor_widget.index('insert').split('.')

    def update_text(self, text):
        tokens = self.compiler.use_lexer(text)

        cursor_y, cursor_x = self.get_cursor_position()
        self.editor.update('')

        for i, token in enumerate(tokens):
            if i >= len(tokens) - 2:
                continue

            try:
                previous_token = tokens[i - 1]
            except IndexError:
                previous_token = None

            # # intend
            # if previous_token and isinstance(previous_token, EndOfLineToken):
            #     indent_str = get_suggested_intend_after_line(tokens, token.line.line_index - 1)
            #     self.editor.update(indent_str, append=True)
            #     cursor_x = int(cursor_x) + len(indent_str)

            color = token.get_meta_data_for_sequence(tokens).get('color')
            self.editor.update(str(token), text_color_for_value=color, append=True)

        self.set_cursor_position(y=cursor_y, x=cursor_x)
