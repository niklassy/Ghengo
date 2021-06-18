import pytest

from django_meta.project import DjangoProject
from gherkin.settings import Settings


@pytest.fixture(autouse=True)
def run_around_tests():
    """For now the settings are used for the language, in some tests that language may be changed, so reset it here."""
    Settings.language = Settings.DEFAULT_LANGUAGE
    yield
    Settings.language = Settings.DEFAULT_LANGUAGE


@pytest.fixture(scope="session", autouse=True)
def prepare_django_project(request):
    DjangoProject('django_sample_project.apps.config.settings')
