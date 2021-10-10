# number of spaces for an indent in Python
import argparse
import os
import re

from dotenv import load_dotenv

from core.constants import GenerationType

PYTHON_INDENT_SPACES = 4
GHERKIN_INDENT_SPACES = 2


class SettingsBase:
    """
    Settings that can/ will be changed during runtime and generation of code.
    """
    class Defaults:
        MEASURE_PERFORMANCE = False
        GENERATE_TEST_TYPE = GenerationType.PY_TEST
        DJANGO_SETTINGS_PATH = None
        DJANGO_APPS_FOLDER = None
        TEST_EXPORT_DIRECTORY = 'generated_tests/'
        TEST_IMPORT_FILE = None

    def __init__(self):
        # these are values that may change curing generation
        self.language = None
        self.django_project_wrapper = None

        # these are values that are set in stone once the generations starts
        self.GENERATE_TEST_TYPE = None
        self.DJANGO_SETTINGS_PATH = None
        self.TEST_EXPORT_DIRECTORY = None
        self.TEST_IMPORT_FILE = None
        self.MEASURE_PERFORMANCE = False
        self.DEEPL_API_KEY = None
        self.DEEPL_USE_FREE_API = True
        self.DJANGO_APPS_FOLDER = None

        # step 1) read values from the .env
        self._env_loaded = False
        self._read_env()

        # step 2) set the default values
        self._set_defaults()

        # step 3) read values from arguments in the command line and overwrite the values
        self._read_arguments()

        # step 4) validate settings
        self._validate()

    def _read_env(self):
        if not self._env_loaded:
            load_dotenv()
        self.DEEPL_API_KEY = os.getenv('DEEPL_API_KEY')
        self.DEEPL_USE_FREE_API = os.getenv('DEEPL_USE_FREE_API') == 'True'
        self._env_loaded = True

    def _set_defaults(self):
        self.GENERATE_TEST_TYPE = self.Defaults.GENERATE_TEST_TYPE
        self.DJANGO_SETTINGS_PATH = self.Defaults.DJANGO_SETTINGS_PATH
        self.TEST_EXPORT_DIRECTORY = self.Defaults.TEST_EXPORT_DIRECTORY
        self.DJANGO_APPS_FOLDER = self.Defaults.DJANGO_APPS_FOLDER
        self.TEST_IMPORT_FILE = self.Defaults.TEST_IMPORT_FILE
        self.MEASURE_PERFORMANCE = self.Defaults.MEASURE_PERFORMANCE

    def _validate(self):
        # ignore validation for tests
        if os.environ.get('RUNNING_TESTS') == 'True':
            return

        if not self.DEEPL_API_KEY:
            raise ValueError('You must provide a DEEPL_API_KEY in a .env file.')

    def reset(self):
        self._set_defaults()

    @staticmethod
    def _is_folder_path(string, absolute=False):
        """Check if a string is a valid path to a folder. Set absolute to check if the string should be absolute."""
        end_str = '((\w+)\/)*((\w+)(\/)?)$'
        if absolute:
            end_str = '\/' + end_str

        end_str = '^' + end_str

        return re.match(end_str, string)

    @staticmethod
    def _is_module_path(string):
        """Check if a string is a valid module path (one that would be used as an import)."""
        return re.match(r'^(\w)+(\.\w+)*$', string)

    @staticmethod
    def _is_feature_file_path(string):
        """Check if a string is a valid path to a feature file."""
        return re.match(r'((\w+)\/)*(\w)+\.feature$', string)

    def _read_arguments(self):
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
        args, _ = parser.parse_known_args()

        django_app_folder = args.apps
        django_settings_path = args.settings
        export_directory = args.export_dir
        feature_file_path = args.feature

        if django_app_folder:
            if not self._is_folder_path(django_app_folder, absolute=True):
                raise ValueError(
                    'You must pass a folder path to the apps in the format `/my/absolute/path/to/apps` '
                    '(you provided `{}`)'.format(django_app_folder)
                )
            self.DJANGO_APPS_FOLDER = django_app_folder

        if django_settings_path:
            if not self._is_module_path(django_settings_path):
                raise ValueError(
                    'You must pass a folder path to the django settings in the format `apps.to.settings` '
                    '(you provided `{}`)'.format(django_settings_path)
                )

            self.DJANGO_SETTINGS_PATH = django_settings_path

        if export_directory:
            if not self._is_folder_path(export_directory, absolute=False):
                raise ValueError(
                    'You must pass a folder path where Ghengo should export files in the format '
                    '`/my/absolute/path/to/export_dir` (you provided `{}`)'.format(export_directory)
                )
            self.TEST_EXPORT_DIRECTORY = export_directory

        if feature_file_path:
            if not self._is_feature_file_path(feature_file_path):
                raise ValueError(
                    'You must pass the path to the feature file that is imported in the format '
                    '`/my/absolute/path/to/file.feature` (you provided `{}`)'.format(feature_file_path)
                )

            self.TEST_IMPORT_FILE = feature_file_path


