import importlib
import os

from django.apps import apps
from django import setup
from django.conf import settings


class ModelInterface(object):
    def __init__(self, model):
        self.model = model

    @property
    def verbose_name(self):
        return self.model._meta.verbose_name


class DjangoProject(object):
    def __init__(self, settings_path):
        self.settings = importlib.import_module(settings_path)
        os.environ['DJANGO_SETTINGS_MODULE'] = settings_path
        setup()
        a = self.get_apps()
        b = self.get_apps(include_django=False, include_third_party=True)
        c = self.get_apps(include_django=True, include_third_party=False)
        d = self.get_apps(include_django=True, include_third_party=True)

    def app_defined_by_project(self, app):
        """Check if a given app is defined by the project itself (not from django or third-party)"""
        return self.settings.BASE_DIR in app.path

    def app_defined_by_django(self, app):
        """Check if a given app is from django."""
        return app.name.startswith('django.')

    def app_defined_by_third_party(self, app):
        """Check if a given app is coming from a third party library."""
        return not self.app_defined_by_project(app)

    def get_apps(self, include_django=False, include_third_party=False, include_project=True):
        # get all apps from application
        all_apps = list(apps.get_app_configs())

        # if all should be returned, return here
        if include_django and include_third_party and include_project:
            return all_apps

        output = []

        # TODO: maybe remove from list afterwards for performance?
        if include_django:
            for app in all_apps:
                if self.app_defined_by_django(app):
                    output.append(app)

        if include_third_party:
            for app in all_apps:
                if self.app_defined_by_third_party(app) and not self.app_defined_by_django(app) and app not in output:
                    output.append(app)

        if include_project:
            for app in all_apps:
                if self.app_defined_by_project(app) and app not in output:
                    output.append(app)

        return output

    def get_models(self, include_django=False, include_third_party=False, include_project=True):
        output = []
        project_apps = self.get_apps(
            include_django=include_django, include_third_party=include_third_party, include_project=include_project)

        for app in project_apps:
            for model in app.get_models():
                output.append(model)

        return output
