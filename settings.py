# number of spaces for an indent in Python
from core.constants import Languages

PYTHON_INDENT_SPACES = 4
GHERKIN_INDENT_SPACES = 2


class GenerationType:
    PY_TEST = 'py_test'


class _Settings:
    """
    Settings that can/ will be changed during runtime and generation of code.
    """
    class Defaults:
        LANGUAGE = Languages.EN
        GENERATE_TEST_TYPE = GenerationType.PY_TEST
        DJANGO_SETTINGS_PATH = 'django_sample_project.apps.config.settings'

    language = Defaults.LANGUAGE
    generate_test_type = Defaults.GENERATE_TEST_TYPE
    django_settings_path = Defaults.DJANGO_SETTINGS_PATH

    def reset(self):
        """Reset the settings to the default values."""
        self.language = self.Defaults.LANGUAGE
        self.generate_test_type = self.Defaults.GENERATE_TEST_TYPE


Settings = _Settings()
