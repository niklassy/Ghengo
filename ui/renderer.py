from gherkin.compiler import GherkinToPyTestCompiler
from gherkin.utils import get_sequence_as_lines, get_indent_level_for_next_line
from settings import GHERKIN_INDENT_SPACES
from ui.window import WindowValues


class _RenderHistory(object):
    def __init__(self):
        self.last_render_meta = {}

    def add_render_information(self, key, value):
        self.last_render_meta[key] = value


RenderHistory = _RenderHistory()


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

        self._last_token_classes = []

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
        last_tokens = RenderHistory.last_render_meta.get('last_token_classes', [])

        # no need to re-render if all tokens stayed the same
        if len(tokens) == len(last_tokens) and all([isinstance(t, last_tokens[i]) for i, t in enumerate(tokens)]):
            return

        cursor_y, cursor_x = self.get_cursor_position()
        self.editor.update('')

        lines = get_sequence_as_lines(tokens)
        for i, token in enumerate(tokens):
            # skip the EOF and the last EndOfLine token
            if i >= len(tokens) - 2:
                continue

            # # intend
            token_line_index = token.line.line_index
            try:
                last_time_class = last_tokens[i]
            except IndexError:
                last_time_class = None

            token_has_changed = last_time_class != token.__class__
            first_token_in_line = token == lines[token_line_index][0]
            token_at_cursor_line = int(cursor_y) - 1 == token.line.line_index

            with_indent = first_token_in_line
            if token_at_cursor_line and first_token_in_line and token_has_changed:
                indent_lvl = get_indent_level_for_next_line(
                    tokens=tokens,
                    line_index=token_line_index,
                    filter_token=token,
                )
                indent = GHERKIN_INDENT_SPACES * indent_lvl
                indent_str = ' ' * indent

                if indent_lvl >= 0:
                    token.line.text = indent_str + token.line.text.lstrip()
                    token.line.indent = indent
                    cursor_x = len(token.line.text)

            color = token.get_meta_data_for_sequence(tokens).get('color')
            self.editor.update(token.to_string(with_indent), text_color_for_value=color, append=True)

        RenderHistory.add_render_information('last_token_classes', [token.__class__ for token in tokens])
        self.set_cursor_position(y=cursor_y, x=cursor_x)
