# Django-Gherkin Test Generator

## Setup
You need to install Pipenv first.

Install all libraries:
```bash
pipenv install
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
