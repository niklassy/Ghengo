from django_meta.setup import setup_django
import PySimpleGUI as sg

from gherkin.exception import GherkinInvalid
from gherkin.token import EndOfLineToken
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
    while True:
        event, values = window.read()
        if event == sg.WIN_CLOSED or event == 'Cancel':  # if user closes window or clicks cancel
            break

        text = values['GHERKIN_EDITOR']

        tokens = c.use_lexer(text)

        # add simple styling
        # reset the value and go through each token
        window['GHERKIN_EDITOR'].update('')
        for i, token in enumerate(tokens):
            try:
                previous_token = tokens[i - 1]
            except IndexError:
                previous_token = None

            if previous_token and isinstance(previous_token, EndOfLineToken):
                window['GHERKIN_EDITOR'].update(token.line.intend_as_string, append=True)
            color = token.get_meta_data_for_sequence(tokens).get('color')
            window['GHERKIN_EDITOR'].update(str(token), text_color_for_value=color, append=True)

        try:
            c.compile_text(text)
            window['ERROR_MESSAGE'].update('')
        except GherkinInvalid as e:
            window['ERROR_MESSAGE'].update(str(e))
            continue

        text = c.export_as_text()
        window['OUTPUT_FIELD'].update(text)

    window.close()
