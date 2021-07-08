from django_meta.setup import setup_django
import pytest
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
