from django_meta.setup import setup_django
import PySimpleGUI as sg

from gherkin.exception import GherkinInvalid
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
        window['GHERKIN_EDITOR'].update(text, text_color_for_value='blue')

        try:
            c.compile_text(text)
            window['ERROR_MESSAGE'].update('')
        except GherkinInvalid as e:
            window['ERROR_MESSAGE'].update(str(e))
            continue

        text = c.export_as_text()
        window['OUTPUT_FIELD'].update(text)

    window.close()
