# number of spaces for an indent in Python
import argparse
import os
import re

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
        MEASURE_PERFORMANCE = False
        GENERATE_TEST_TYPE = GenerationType.PY_TEST
        DJANGO_SETTINGS_PATH = None
        DJANGO_APPS_FOLDER = None
        TEST_EXPORT_DIRECTORY = 'generated_tests/'
        TEST_IMPORT_FILE = 'django_sample_project/features/variable_reference.feature'
        DJANGO_PROJECT_WRAPPER = None

    # the language in gherkin
    language = Defaults.LANGUAGE

    # the tests that are generated
    generate_test_type = Defaults.GENERATE_TEST_TYPE

    # the settings path to the django project
    django_settings_path = Defaults.DJANGO_SETTINGS_PATH
    django_apps_folder = Defaults.DJANGO_APPS_FOLDER

    # the directory to which tests are exported to
    test_export_directory = Defaults.TEST_EXPORT_DIRECTORY

    # the gherkin file which is imported
    test_import_file = Defaults.TEST_IMPORT_FILE

    # set if Ghengo should measure its performance and print out information at the end
    measure_performance = Defaults.MEASURE_PERFORMANCE

    # Django uses this to store an instance of the django project
    django_project_wrapper = Defaults.DJANGO_PROJECT_WRAPPER

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
        self.measure_performance = self.Defaults.MEASURE_PERFORMANCE
        self.django_project_wrapper = self.Defaults.DJANGO_PROJECT_WRAPPER


Settings = _Settings()


def _is_folder_path(string, absolute=False):
    """Check if a string is a valid path to a folder. Set absolute to check if the string should be absolute."""
    end_str = '((\w+)\/)*((\w+)(\/)?)$'
    if absolute:
        end_str = '\/' + end_str

    end_str = '^' + end_str

    return re.match(end_str, string)


def _is_module_path(string):
    """Check if a string is a valid module path (one that would be used as an import)."""
    return re.match(r'^(\w)+(\.\w+)*$', string)


def _is_feature_file_path(string):
    """Check if a string is a valid path to a feature file."""
    return re.match(r'((\w+)\/)*(\w)+\.feature$', string)


def read_arguments():
    """
    Reads all the arguments that are provided by the command line and saves them in the Settings object.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--apps',
        type=str,
        help='The path to all the apps of a django project. Please add an absolute, full path here, '
             'like: /User/.../apps/'
    )
    parser.add_argument(
        '--settings',
        type=str,
        help='The module path to the settings that would be used in your code to get the settings of Django, '
             'like: apps.config.settings'
    )
    parser.add_argument(
        '--export-dir',
        type=str,
        help='The directory to which Ghengo will export the test files. Like: `generated_tests/`'
    )
    parser.add_argument(
        '--feature',
        type=str,
        help='The feature file that Ghengo will use as an import to generate tests. Like: features/foo.feature'
    )
    args = parser.parse_args()

    django_app_folder = args.apps
    django_settings_path = args.settings
    export_directory = args.export_dir
    feature_file_path = args.feature

    if django_app_folder:
        if not _is_folder_path(django_app_folder, absolute=True):
            raise ValueError(
                'You must pass a folder path to the apps in the format `/my/absolute/path/to/apps` '
                '(you provided `{}`)'.format(django_app_folder)
            )
        Settings.django_apps_folder = django_app_folder

    if django_settings_path:
        if not _is_module_path(django_settings_path):
            raise ValueError(
                'You must pass a folder path to the django settings in the format `apps.to.settings` '
                '(you provided `{}`)'.format(django_settings_path)
            )

        Settings.django_settings_path = django_settings_path

    if export_directory:
        if not _is_folder_path(export_directory, absolute=False):
            raise ValueError(
                'You must pass a folder path where Ghengo should export files in the format '
                '`/my/absolute/path/to/export_dir` (you provided `{}`)'.format(export_directory)
            )
        Settings.test_export_directory = export_directory

    if feature_file_path:
        if not _is_feature_file_path(feature_file_path):
            raise ValueError(
                'You must pass the path to the feature file that is imported in the format '
                '`/my/absolute/path/to/file.feature` (you provided `{}`)'.format(feature_file_path)
            )

        Settings.test_import_file = feature_file_path
