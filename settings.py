# number of spaces for an indent in Python
import os

from dotenv import load_dotenv

from core.constants import Languages

PYTHON_INDENT_SPACES = 4
GHERKIN_INDENT_SPACES = 2


# load the .env
load_dotenv()


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
        TEST_EXPORT_DIRECTORY = 'generated_tests/'
        TEST_IMPORT_FILE = 'django_sample_project/features/bewertung_s1.feature'

    # the language in gherkin
    language = Defaults.LANGUAGE

    # the tests that are generated
    generate_test_type = Defaults.GENERATE_TEST_TYPE

    # the settings path to the django project
    django_settings_path = Defaults.DJANGO_SETTINGS_PATH

    # the directory to which tests are exported to
    test_export_directory = Defaults.TEST_EXPORT_DIRECTORY

    # the gherkin file which is imported
    test_import_file = Defaults.TEST_IMPORT_FILE

    # == values that are imported from .env and are constants ==
    DEEPL_API_KEY = os.getenv('DEEPL_API_KEY')
    DEEPL_USE_FREE_API = os.getenv('DEEPL_USE_FREE_API') == 'True'

    def reset(self):
        """Reset the settings to the default values."""
        self.language = self.Defaults.LANGUAGE
        self.generate_test_type = self.Defaults.GENERATE_TEST_TYPE
        self.django_settings_path = self.Defaults.DJANGO_SETTINGS_PATH
        self.test_export_directory = self.Defaults.TEST_EXPORT_DIRECTORY
        self.test_import_file = self.Defaults.TEST_IMPORT_FILE


Settings = _Settings()
