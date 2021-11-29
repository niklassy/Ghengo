# Ghengo - Django-Gherkin Test Generator

This software was created during a master's thesis at [Hochschule der Medien](https://www.hdm-stuttgart.de/) in
cooperation with [Ambient](https://ambient.digital/).

With this project you are able to generate code with natural language for a Django API. In this case Gherkin can be
used to create test cases. Right now this project is only able to generate pytest for Python.
The software is fully tested for German Gherkin. Some parts work for an English file as well.

The UI for this was not the main part of the project and it is somewhat wonky and
slow. You can still use it to try some stuff.

Here is an example for how the code generation can look like. The Gherkin input:

```Gherkin
# language: de
Funktionalität: Anfragen für Aufträge
  Szenario: Auftragsliste ohne Authentifizierung
    Wenn die Liste der Aufträge geholt wird
    Dann sollte die Antwort keine Einträge haben

  Szenario: Nutzer holt Auftragsliste
    Gegeben sei ein Benutzer Alice mit dem Vornamen Alice
    Und ein Auftrag mit dem Besitzer Alice und der Nummer 1
    Wenn Alice die Liste der Aufträge holt
    Dann sollte die Antwort einen Auftrag enthalten
    Und der erste Eintrag sollte die Nummer 1 haben
```

Would be used to generate the following test cases for PyTest:

```Python
from rest_framework.test import APIClient
from django.urls import reverse
import pytest


def test_order_list_without_authentication():
    client = APIClient()
    response = client.get(reverse('orders-list'))
    assert len(response.data) == 0


@pytest.mark.django_db
def test_user_fetches_order_list(user_factory, order_factory):
    alice = user_factory(first_name='Alice')
    order_factory(owner=alice, number=1)
    client = APIClient()
    client.force_authenticate(alice)
    response = client.get(reverse('orders-list'))
    assert len(response.data) == 1
    entry_0 = response.data[0]
    assert entry_0.get('number') == 1
```

## Read about the software

If you want to read more about the code, the conceptual design or need some background information
you can read the thesis or a short paper [here](/thesis).

## Features

The software tries to determine different actions that are usually created in code
when testing a Django API. You can find some examples of the translations from
natural language to code [here](/demo).

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
Use this command after setting all values in the settings.py

```bash
pipenv run python main.py
```

OR

Use this command and fill out everything that is needed:

```bash
pipenv run python main.py --apps /User/.../apps/ --settings apps.config.settings --export-dir generated_tests/ --feature django_sample_project/features/variable_reference.feature
```

The same arguments apply for the following commands.

Also, run this for help:

```bash
pipenv run python main.py -h
```

## Open the UI
```bash
pipenv run python main_ui.py
```

## Start Django sample

This repository contains a sample django project as an example. You can run
the django application with this command:

```bash
pipenv run python manage.py runserver
```

## Measure the performance

If you want to measure the performance of Ghengo, use this command:

Run in root of project:
```bash
pipenv run python main_measure.py
```
