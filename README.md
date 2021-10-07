# Ghengo - Django-Gherkin Test Generator

## What is this?
With this project you are able to generate code with natural language. In this case Gherkin can be
used to create test cases. Right now this project is only able to generate pytest for Python.
It is fully tested for German but it also works in English. But it does not work as well in English as in German.

Here you can see it in action. The UI for this was not the main part of the project and it is somewhat wonky and
slow. You can still use it to try some stuff.

Here are some features:

### Creating models and referencing each other

![Creating model entries](demo/gif/model_creation.gif)

### Creating files

![Creating an uploaded file](demo/gif/file_creation.gif)

### Making requests
![Making requests](demo/gif/requests.gif)

### Analyzing list responses
![Checking list responses](demo/gif/list_response.gif)

### Analyzing simple responses
![Checking simple responses](demo/gif/single_entry_resp.gif)

### Analyzing database
![Accesing the database](demo/gif/queryset.gif)

### Analyzing earlier model entries
![Checking previous model entries](demo/gif/previous_model.gif)

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

During development these versions were installed:
``` 
setuptools: 53.0.0
wheel: 0.36.2
```

Install the NLP models from spacy. You can find all the names of the required packages in `nlp/setup`.
You have to make sure that you install a model version that is compatible with the current spacy version.
You can find the compatible versions [here](https://github.com/explosion/spacy-models/blob/master/compatibility.json).

> **Note**: While creating the README, the version for spacy was `3.1.0`. Please have a look at the `Pipfile` to double 
> check that it is still correct.


```bash
pipenv run python -m spacy download en_core_web_lg-<VERSION> --direct
pipenv run python -m spacy download de_core_news_lg-<VERSION> --direct
```

> Examples:
> 
> `pipenv run python -m spacy download en_core_web_lg-3.1.0 --direct`
> 
> `pipenv run python -m spacy download de_core_news_lg-3.1.0 --direct`

Create an env file afterwards. You need to fill in the **value for the API key for DeepL**. You can create a free
account on their website. It can also be upgraded later.

```bash
cp .env.example .env
```

## Start test generator
```bash
pipenv run python main.py
```

## Open the UI
```bash
pipenv run python main_ui.py
```

## Start Django sample

Run in root of project:
```bash
pipenv run python manage.py runserver
```

## Measure the performance

Run in root of project:
```bash
pipenv run python main_measure.py
```
