import json
import os

LANGUAGES_FILE_NAME = 'languages.json'

this_file_path = os.path.abspath(__file__).split('/')

folder_path = this_file_path[:len(this_file_path) - 1]
folder_path.append(LANGUAGES_FILE_NAME)

with open('/'.join(folder_path)) as gherkin_languages:
    GHERKIN_CONFIG = json.load(gherkin_languages)
