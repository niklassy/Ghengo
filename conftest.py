import pytest

from settings import Settings


@pytest.fixture(autouse=True)
def run_around_tests():
    Settings.language = Settings.DEFAULT_LANGUAGE
    yield
    Settings.language = Settings.DEFAULT_LANGUAGE
