# Django-Gherkin Test Generator

## Setup
You need to install Pipenv first.

Install all libraries:
```bash
pipenv install
```

You also may need to install setuptools:
```bash
pipenv install setuptools

# Original command from pip (probably not needed since it is done by pipenv):
pip install -U pip setuptools wheel
```

Install the NLP models from spacy. You can find all the names of the required packages in `nlp/setup`.
```bash
pipenv run python -m spacy download en_core_web_lg
pipenv run python -m spacy download de_core_news_lg
```

## Start test generator
```bash
pipenv run python main.py
```

## Start Django sample

Run in root of project:
```bash
pipenv run python manage.py runserver
```
