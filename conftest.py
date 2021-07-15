from core.constants import Languages
from django_meta.setup import setup_django
import pytest

from nlp.setup import Nlp
from settings import Settings


# setup django before collecting all the tests
setup_django('django_sample_project.apps.config.settings')


@pytest.fixture(autouse=True)
def run_around_tests():
    """For now the settings are used for the language, in some tests that language may be changed, so reset it here."""
    Settings.language = Settings.Defaults.LANGUAGE
    Settings.generate_test_type = None
    yield
    Settings.reset()


@pytest.fixture
def nlp_de():
    return Nlp.for_language(Languages.DE)


@pytest.fixture
def nlp_en():
    return Nlp.for_language(Languages.EN)
