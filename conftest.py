import pytest

from django_meta.project import DjangoProject
from gherkin.settings import Settings
from nlp.generate.settings import GenerationSettings


@pytest.fixture(autouse=True)
def run_around_tests():
    """For now the settings are used for the language, in some tests that language may be changed, so reset it here."""
    Settings.language = Settings.DEFAULT_LANGUAGE
    GenerationSettings.test_type = None
    yield
    GenerationSettings.test_type = GenerationSettings.DEFAULT_TEST_TYPE
    Settings.language = Settings.DEFAULT_LANGUAGE


@pytest.fixture(scope="session", autouse=True)
def prepare_django_project(request):
    DjangoProject('django_sample_project.apps.config.settings')
