import os

from django import setup


def setup_django(settings_path):
    """Sets up django."""
    if 'DJANGO_SETTINGS_MODULE' not in os.environ:
        print('Setting up Django...')
        os.environ['DJANGO_SETTINGS_MODULE'] = settings_path
        setup()
        print('Django is ready!')
