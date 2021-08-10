from django_meta.setup import setup_django
import PySimpleGUI as sg

from gherkin.exception import GherkinInvalid
from gherkin.token import CommentToken
from nlp.setup import Nlp
from ui.window import WindowValues


def run_ui():
    setup_django('django_sample_project.apps.config.settings')
    # all imports must follow the setup!!
    from gherkin.compiler import GherkinToPyTestCompiler
    from ui.autocomplete import AutoCompleteMultiLine
    from gherkin.utils import get_token_suggestion_after_line, get_sequence_as_lines

    Nlp.setup_languages(['de', 'en'])

    multi_line_size = 70

    layout = [
        [
            sg.Text(
                'Enter your Gherkin here. You can press Command/Control + g to generate.',
                size=(int(multi_line_size * 1.5), 1)
            ),
            sg.Text('The output will be here:', size=(int(multi_line_size * 1.5), 1)),
        ],
        [
            sg.Multiline(size=(multi_line_size, 40), font=('Courier', 15), autoscroll=True, key='GHERKIN_EDITOR'),
            sg.Multiline('This will contain the output...', size=(multi_line_size, 40), font=('Courier', 15),
                         key='OUTPUT_FIELD'),
            AutoCompleteMultiLine.as_ui(),
        ],
        [
            sg.Text('Errors will appear here:'),
            sg.Text(
                '',
                size=(int(int(multi_line_size * 1.5) * 1.8), 1),
                key='ERROR_MESSAGE',
                text_color='red',
                background_color='white',
            ),
        ],
        [sg.Button('Generate tests...')]
    ]

    # Create the Window
    window = sg.Window('Ghengo - Django-Gherkin Test Generator', layout)

    c = GherkinToPyTestCompiler()
    last_gherkin_text = ''

    window.finalize()

    def on_generate_tests(bound_event=None, input_text=None):
        assert bound_event or input_text

        window['ERROR_MESSAGE'].update('')
        if bound_event:
            input_text = bound_event.widget.get("1.0", 'end')

        if input_text == '\n':
            return
        window['OUTPUT_FIELD'].update('Loading...')

        try:
            c.compile_text(input_text)
        except GherkinInvalid as e:
            window['ERROR_MESSAGE'].update(str(e))
            return

        window['OUTPUT_FIELD'].update(c.export_as_text())

    window['GHERKIN_EDITOR'].Widget.bind('<Command-g>', on_generate_tests)
    window['GHERKIN_EDITOR'].Widget.bind('<Control-g>', on_generate_tests)

    while True:
        event, values = window.read(timeout=25)
        # do this always first
        WindowValues.set_values(values)

        if event == sg.WIN_CLOSED or event == 'Cancel':  # if user closes window or clicks cancel
            break

        text = values['GHERKIN_EDITOR']

        gherkin_text = text.replace(' ', '')
        if not gherkin_text or (gherkin_text == last_gherkin_text and event == '__TIMEOUT__'):
            last_gherkin_text = gherkin_text
            continue

        last_gherkin_text = gherkin_text

        tokens = c.use_lexer(text)

        from ui.renderer import GherkinEditorRenderer
        editor_renderer = GherkinEditorRenderer(window=window, editor=window['GHERKIN_EDITOR'])
        editor_renderer.update_text(text)

        lines = get_sequence_as_lines(tokens)
        cursor_y, cursor_x = editor_renderer.get_cursor_position()
        tokens_in_line_of_cursor = lines[int(cursor_y) - 1]
        length_first_token = len(tokens_in_line_of_cursor[0].to_string(True))

        # autocomplete
        if event == '__TIMEOUT__':
            if int(cursor_x) > length_first_token and not isinstance(tokens_in_line_of_cursor[0], CommentToken) or text == '\n':
                auto_complete = AutoCompleteMultiLine(
                    window=window,
                    editor=window['GHERKIN_EDITOR'],
                    values=values,
                    text_to_replace='',
                )
                auto_complete.set_values([])
                continue

            suggested_tokens = get_token_suggestion_after_line(tokens, int(cursor_y) - 1)

            raw_autocomplete_suggestions = [keyword for token in suggested_tokens for keyword in token.get_keywords()]
            try:
                current_line = get_sequence_as_lines(tokens)[int(cursor_y) - 1]
            except IndexError:
                pass
            else:
                line_text = current_line[0].line.trimmed_text
                clean_suggestions = [s for s in raw_autocomplete_suggestions if line_text in s and line_text != s]
                auto_complete = AutoCompleteMultiLine(
                    window=window,
                    editor=window['GHERKIN_EDITOR'],
                    values=values,
                    text_to_replace=line_text,
                )
                auto_complete.set_values(clean_suggestions)

                # hide the autocomplete window if there are no suggestions
                if len(clean_suggestions) == 0:
                    auto_complete.hide()
                else:
                    auto_complete.show_at(x=int(cursor_x) * 5 + 10, y=int(cursor_y) * 16 + 20)
            continue

        on_generate_tests(input_text=text)

    window.close()
