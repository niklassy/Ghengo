import os
import sys

from django import setup

from settings import Settings

ENV_SETTINGS_KEY = 'DJANGO_SETTINGS_MODULE'


def setup_django(settings_path):
    """Sets up django."""
    if ENV_SETTINGS_KEY not in os.environ:
        print('Setting up Django...')
        sys.path.insert(1, Settings.django_apps_folder)
        os.environ[ENV_SETTINGS_KEY] = settings_path
        setup()
        print('Django is ready!')
    elif os.environ[ENV_SETTINGS_KEY] != settings_path:
        os.environ[ENV_SETTINGS_KEY] = settings_path
