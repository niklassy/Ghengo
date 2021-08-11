import os

from django import setup

ENV_SETTINGS_KEY = 'DJANGO_SETTINGS_MODULE'


def setup_django(settings_path):
    """Sets up django."""
    if ENV_SETTINGS_KEY not in os.environ:
        print('Setting up Django...')
        os.environ[ENV_SETTINGS_KEY] = settings_path
        setup()
        print('Django is ready!')
    elif os.environ[ENV_SETTINGS_KEY] != settings_path:
        os.environ[ENV_SETTINGS_KEY] = settings_path
