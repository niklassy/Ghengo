import json


with open('languages.json') as gherkin_languages:
    GHERKIN_CONFIG = json.load(gherkin_languages)
