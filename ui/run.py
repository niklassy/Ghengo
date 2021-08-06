from django_meta.setup import setup_django
import PySimpleGUI as sg

from gherkin.exception import GherkinInvalid
from gherkin.token import EndOfLineToken, EmptyToken
from nlp.setup import Nlp


def run_ui():
    setup_django('django_sample_project.apps.config.settings')
    # all imports must follow the setup!!
    from gherkin.compiler import GherkinToPyTestCompiler
    from ui.autocomplete import AutoCompleteMultiLine
    from gherkin.utils import get_suggested_intend_after_line, get_token_suggestion_after_line, get_sequence_as_lines

    # Nlp.setup_languages(['de', 'en'])

    multi_line_size = 70

    layout = [
        [
            sg.Text('Enter your Gherkin here:', size=(int(multi_line_size * 1.5), 1)),
            sg.Text('The output will be here:', size=(int(multi_line_size * 1.5), 1)),
        ],
        [
            sg.Multiline(size=(multi_line_size, 40), font=('Courier', 15), autoscroll=True, key='GHERKIN_EDITOR'),
            sg.Multiline('This will contain the output...', size=(multi_line_size, 40), font=('Courier', 15),
                         key='OUTPUT_FIELD'),
            AutoCompleteMultiLine.as_ui(),
        ],
        [
            sg.Text('', size=(150, 1), key='ERROR_MESSAGE'),
        ],
        [sg.Button('Show'), sg.Button('Exit')]
    ]

    # Create the Window
    window = sg.Window('Window Title', layout)

    c = GherkinToPyTestCompiler()
    last_gherkin_text = ''

    window.finalize()
    # TODO: add control s to convert!
    # window['GHERKIN_EDITOR'].Widget.bind('<Control-S>')
    # window['AUTOCOMPLETE'].Widget.place(x=10, y=15) DAS GEHT!!!!

    while True:
        event, values = window.read(timeout=5)
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

        # add simple styling
        # reset the value and go through each token
        # save the cursor position
        cursor_y, cursor_x = editor_renderer.get_cursor_position()
        window['ERROR_MESSAGE'].update('')

        # autocomplete
        if event == '__TIMEOUT__':
            raw_autocomplete_suggestions = get_token_suggestion_after_line(tokens, int(cursor_y) - 1)
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

        try:
            c.compile_text(text)
        except GherkinInvalid as e:
            window['ERROR_MESSAGE'].update(str(e))
            continue

        text = c.export_as_text()
        window['OUTPUT_FIELD'].update(text)

    window.close()
