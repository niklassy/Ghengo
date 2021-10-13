from core.constants import GenerationType
from core.settings import SettingsBase


class _Settings(SettingsBase):
    class Defaults(SettingsBase.Defaults):
        MEASURE_PERFORMANCE = False
        GENERATE_TEST_TYPE = GenerationType.PY_TEST
        DJANGO_SETTINGS_PATH = 'django_sample_project.apps.config.settings'
        # DJANGO_APPS_FOLDER = None     <- overwrite this if necessary; it needs to be an absolute path; like:
        #                                   /Users/name/...(project/apps
        TEST_EXPORT_DIRECTORY = 'generated_tests/'
        TEST_IMPORT_FILE = 'django_sample_project/features/bewertung_s5.feature'


Settings = _Settings()
