import os

from core.constants import Languages
from django_meta.setup import setup_django
import pytest

from nlp.setup import Nlp
from settings import Settings


Settings.django_settings_path = 'django_sample_project.apps.config.settings'
Settings.django_apps_folder = '/Users/niklas/HdM/Master_CSM/Masterarbeit/project/django_sample_project/apps'


# setup django before collecting all the tests
setup_django('django_sample_project.apps.config.settings')


def pytest_generate_tests(metafunc):
    os.environ['RUNNING_TESTS'] = 'True'


@pytest.fixture(autouse=True)
def run_around_tests():
    """For now the settings are used for the language, in some tests that language may be changed, so reset it here."""
    Settings.language = Settings.Defaults.LANGUAGE
    Settings.generate_test_type = None

    # no api key for deepl while testing
    Settings.DEEPL_API_KEY = 'INVALID_API_KEY_jer&&&iu23p48sldfjhjkl9'
    yield
    Settings.reset()


@pytest.fixture
def nlp_de():
    return Nlp.for_language(Languages.DE)


@pytest.fixture
def nlp_en():
    return Nlp.for_language(Languages.EN)
