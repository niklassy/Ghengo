import os
from pathlib import Path

from core.constants import Languages
import pytest
from nlp.setup import Nlp
from core.settings import SettingsBase

# keep this here, must come before import of settings and setup of django
SettingsBase.validate = False

from django_meta.setup import setup_django
from settings import Settings

Settings.Defaults.DJANGO_SETTINGS_PATH = 'django_sample_project.apps.config.settings'
Settings.Defaults.DJANGO_APPS_FOLDER = str(Path(__file__).parent.absolute()) + '/django_sample_project/apps'
Settings.DEEPL_API_KEY = 'INVALID_API_KEY_jer&&&iu23p48sldfjhjkl9'

# setup django before collecting all the tests
setup_django('django_sample_project.apps.config.settings')


def pytest_generate_tests(metafunc):
    os.environ['RUNNING_TESTS'] = 'True'


@pytest.fixture(autouse=True)
def run_around_tests():
    """For now the settings are used for the language, in some tests that language may be changed, so reset it here."""
    Settings.language = Languages.EN
    Settings.GENERATE_TEST_TYPE = None
    yield
    Settings.reset()


@pytest.fixture
def nlp_de():
    return Nlp.for_language(Languages.DE)


@pytest.fixture
def nlp_en():
    return Nlp.for_language(Languages.EN)
