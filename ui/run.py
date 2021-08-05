from django_meta.setup import setup_django
import PySimpleGUI as sg

from gherkin.exception import GherkinInvalid
from gherkin.token import EndOfLineToken, EmptyToken
from gherkin.utils import get_suggested_intend_after_line
from nlp.setup import Nlp


def run_ui():
    setup_django('django_sample_project.apps.config.settings')
    # all imports must follow the setup!!
    from gherkin.compiler import GherkinToPyTestCompiler

    Nlp.setup_languages(['de', 'en'])

    layout = [
        [
            sg.Text('Enter your Gherkin here:', size=(150, 1)),
            sg.Text('The output will be here:', size=(150, 1)),
        ],
        [
            sg.Multiline(size=(100, 40), font=('Courier', 15), autoscroll=True, key='GHERKIN_EDITOR'),
            sg.Multiline('This will contain the output...', size=(100, 40), font=('Courier', 15), key='OUTPUT_FIELD'),
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

    while True:
        event, values = window.read(timeout=20)
        if event == sg.WIN_CLOSED or event == 'Cancel':  # if user closes window or clicks cancel
            break

        text = values['GHERKIN_EDITOR']
        gherkin_text = text.replace(' ', '')
        if not gherkin_text or (gherkin_text == last_gherkin_text and event == '__TIMEOUT__'):
            last_gherkin_text = gherkin_text
            continue

        last_gherkin_text = gherkin_text

        tokens = c.use_lexer(text)

        # add simple styling
        # reset the value and go through each token
        # save the cursor position
        editor_widget = window['GHERKIN_EDITOR'].Widget
        cursor_y, cursor_x = editor_widget.index('insert').split('.')
        window['GHERKIN_EDITOR'].update('')

        for i, token in enumerate(tokens):
            if i >= len(tokens) - 2:
                continue

            try:
                previous_token = tokens[i - 1]
            except IndexError:
                previous_token = None

            next_token = tokens[i + 1]

            if previous_token and isinstance(previous_token, EndOfLineToken):
                window['GHERKIN_EDITOR'].update(token.line.intend_as_string, append=True)

            if isinstance(token, EmptyToken) and isinstance(previous_token, EndOfLineToken) and isinstance(next_token, EndOfLineToken):
                if int(cursor_y) - 1 == token.line.line_index:
                    indent_str = get_suggested_intend_after_line(tokens, token.line.line_index - 1)
                    window['GHERKIN_EDITOR'].update(indent_str, append=True)
                    cursor_x = int(cursor_x) + len(indent_str)

            color = token.get_meta_data_for_sequence(tokens).get('color')
            window['GHERKIN_EDITOR'].update(str(token), text_color_for_value=color, append=True)

        editor_widget.mark_set("insert", "%d.%d" % (float(cursor_y), float(cursor_x)))
        window['ERROR_MESSAGE'].update('')

        if event == '__TIMEOUT__':
            # autocomplete
            try:
                c.use_parser(tokens)
            except GherkinInvalid as e:
                next_valid_tokens = e.suggested_tokens
                print('Suggested: ', [t.get_keywords() for t in next_valid_tokens])
            continue

        try:
            c.compile_text(text)
        except GherkinInvalid as e:
            window['ERROR_MESSAGE'].update(str(e))
            continue

        text = c.export_as_text()
        window['OUTPUT_FIELD'].update(text)

    window.close()
