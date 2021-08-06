import PySimpleGUI as sg


class AutoCompleteMultiLine(object):
    """
    This class can be used to display an auto complete in the gherkin editor.
    """
    key = 'AUTOCOMPLETE'

    def __init__(self, window, editor, values, text_to_replace):
        self.text_to_replace = text_to_replace
        self.window = window
        self.editor = editor
        self.editor_value = values[editor.Key]
        self.editor_widget = editor.Widget
        self.ui = window[self.key]
        self.widget = self.ui.Widget
        self.values = []
        self.focused_value_index = 0

        self.ui.update(disabled=True)

        self._old_cursor_position_x = 0
        self._old_cursor_position_y = 0

        self.autocomplete_focused = False

    @classmethod
    def as_ui(cls):
        """Returns the ui element for the autocomplete."""
        return sg.Multiline('', key=cls.key, font=('Courier', 15))

    def set_cursor_position(self):
        """Sets the cursor position in the gherkin editor to the position that was saved."""
        self.editor_widget.mark_set(
            "insert", "%d.%d" % (float(self._old_cursor_position_y), float(self._old_cursor_position_x)))
        self._old_cursor_position_x = 0
        self._old_cursor_position_y = 0

    def get_selected_value(self):
        """Returns the currently value."""
        return self.values[self.focused_value_index]

    def focus_editor(self):
        """All that is needed to focus the gherkin editor again."""
        # autocomplete no longer focused
        self.autocomplete_focused = False
        self.editor.update(disabled=False)

        # reset the focused index
        self.set_focused_index(None)

        # focus the editor again and set the cursor position in the editor
        self.editor_widget.focus_set()
        self.set_cursor_position()

    def focus_auto_complete(self):
        """All that is needed to focus the auto complete."""
        self.save_cursor_position()
        self.widget.focus_set()
        self.editor.update(disabled=True)
        self.autocomplete_focused = True

    def save_cursor_position(self):
        """Saves the current cursor position in the gherkin editor."""
        cursor_y, cursor_x = self.editor_widget.index('insert').split('.')
        self._old_cursor_position_x = cursor_x
        self._old_cursor_position_y = cursor_y

    def on_editor_down(self, *args):
        """Called when <Down> is hit in the editor."""
        self.focus_auto_complete()
        self.on_down()

    def on_editor_enter(self, *args):
        """Called when <Enter> is hit in the editor."""
        self.focus_auto_complete()
        self.on_enter()

        # prevent normal behaviour from the enter
        return 'break'

    def on_escape(self, *args):
        """Called when Escape is hit in the auto complete."""
        self.focus_editor()
        self.hide()

    def on_enter(self, *args):
        """
        Called when <Enter> is hit in the auto complete. It will replace the text and set the value.
        """
        selected_value = self.get_selected_value()
        relevant_line_index = int(self._old_cursor_position_y) - 1
        lines = self.editor_value.split('\n')

        # remove the line that would be created by the return
        try:
            if lines[relevant_line_index + 1] == '':
                lines.pop(relevant_line_index + 1)
        except IndexError:
            pass

        for i, line in enumerate(lines):
            if i == int(relevant_line_index) and self.text_to_replace in line:
                replaced_line = line.replace(self.text_to_replace, selected_value)
                cursor_x = int(self._old_cursor_position_x)

                # set the cursor position to be at the end of the replacement
                self._old_cursor_position_x = cursor_x - len(self.text_to_replace) + len(replaced_line)
                lines[i] = replaced_line

        # update the window with new text
        from ui.renderer import GherkinEditorRenderer
        renderer = GherkinEditorRenderer(window=self.window, editor=self.editor)
        renderer.update_text('\n'.join(lines))
        # focus editor again
        self.focus_editor()

    def set_focused_index(self, index):
        """Set the index of the value that is currently focused."""
        self.focused_value_index = index
        self._draw_options()

    def on_up(self, *args):
        """Called when up is hit in the auto complete."""
        if self.focused_value_index == 0:
            if self.autocomplete_focused:
                self.focus_editor()
            return

        self.set_focused_index(self.focused_value_index - 1)

    def on_down(self, *args):
        """Called when down is hit in the auto complete."""
        if self.focused_value_index == len(self.values) - 1:
            return

        if self.focused_value_index is None:
            self.set_focused_index(0)
        else:
            self.set_focused_index(self.focused_value_index + 1)

    def hide(self, *args):
        """Hides the auto complete box."""
        self.widget.place(x=-100, y=-100)
        self.widget.unbind('<Return>')
        self.widget.unbind('<Up>')
        self.widget.unbind('<Down>')
        self.widget.unbind('<Escape>')
        self.editor_widget.unbind('<Escape>')
        self.editor_widget.unbind('<Down>')
        self.editor_widget.unbind('<Return>')

    def show_at(self, x, y):
        """Shows the auto complete box at given x and y."""
        self.widget.place(x=x, y=y)
        self.widget.bind('<Return>', func=self.on_enter)
        self.widget.bind('<Up>', func=self.on_up)
        self.widget.bind('<Down>', func=self.on_down)
        self.widget.bind('<Escape>', func=self.on_escape)
        self.editor_widget.bind('<Escape>', func=self.hide)
        self.editor_widget.bind('<Down>', func=self.on_editor_down)
        self.editor_widget.bind('<Return>', func=self.on_editor_enter)

    def _draw_options(self):
        """
        Draws out all the value options. This is needed to highlight the selected option.
        """
        self.ui.update('')
        for i, value in enumerate(self.values):
            highlighted = i == self.focused_value_index

            background_color = None
            if highlighted:
                background_color = 'yellow'

            self.ui.update(value, background_color_for_value=background_color, append=True)
            self.ui.update('\n', background_color_for_value=background_color, append=True)

    def set_values(self, values):
        """Set the values/ options of the auto complete."""
        self.values = values
        self._draw_options()
        self.ui.set_size((30, len(self.values)))
