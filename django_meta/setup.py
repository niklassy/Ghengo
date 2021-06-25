import os

from django import setup


def setup_django(settings_path):
    """Sets up django."""
    os.environ['DJANGO_SETTINGS_MODULE'] = settings_path
    setup()
