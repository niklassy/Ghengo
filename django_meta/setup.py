import os
import sys
import warnings

from django import setup

from settings import Settings

ENV_SETTINGS_KEY = 'DJANGO_SETTINGS_MODULE'


def setup_django(settings_path, print_warning=False):
    """Sets up django."""
    if not Settings.DJANGO_APPS_FOLDER or not settings_path:
        if print_warning:
            warnings.warn(
                '\n ================================================================================ \n'
                'You did not provide a path to the apps of a Django project or its settings. Ghengo will \nrun '
                'normally but might not work as well. You can set these values either via adding arguments in the '
                '\ncommand line (execute -h to gain more information) or by setting these values in the settings.py '
                'of Ghengo.'
                '\n ================================================================================ \n'
            )
        return False

    if ENV_SETTINGS_KEY not in os.environ:
        print('Setting up Django...')
        sys.path.insert(1, Settings.DJANGO_APPS_FOLDER)
        os.environ[ENV_SETTINGS_KEY] = settings_path
        setup()
        print('Django is ready!')
    elif os.environ[ENV_SETTINGS_KEY] != settings_path:
        os.environ[ENV_SETTINGS_KEY] = settings_path

    return True
