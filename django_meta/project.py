import importlib
import os

from django.apps import apps
from django import setup
from django.urls import URLPattern, URLResolver, get_resolver


class ModelInterface(object):
    def __init__(self, model):
        self.model = model

    @property
    def verbose_name(self):
        return self.model._meta.verbose_name


class AppInterface(object):
    def __init__(self, app):
        self.app = app

    def get_models(self, as_interface=False):
        output = []

        for model in self.app.get_models():
            if as_interface:
                model = ModelInterface(model)
            output.append(model)

        return output


class DjangoProject(object):
    def __init__(self, settings_path):
        self.settings = importlib.import_module(settings_path)

        # django needs to know where the settings are, so set it in the env and setup django afterwards
        os.environ['DJANGO_SETTINGS_MODULE'] = settings_path
        setup()

    def app_defined_by_project(self, app):
        """Check if a given app is defined by the project itself (not from django or third-party)"""
        return self.settings.BASE_DIR in app.path

    def app_defined_by_django(self, app):
        """Check if a given app is from django."""
        return app.name.startswith('django.')

    def app_defined_by_third_party(self, app):
        """Check if a given app is coming from a third party library."""
        return not self.app_defined_by_project(app) and not self.app_defined_by_django(app)

    def get_reverse_keys(self):
        """Returns all keys that are used in the project that can be used via reverse"""
        return get_resolver().reverse_dict.keys()

    def list_urls(self, url_pattern=None, acc=None):
        """
        Returns all urls that are available in the project.

        Returns:
            [[str]]
        """
        if url_pattern is None:
            url_pattern = __import__(self.settings.ROOT_URLCONF, {}, {}, ['']).urlpatterns

        if acc is None:
            acc = []

        if not url_pattern:
            return

        entry = url_pattern[0]
        if isinstance(entry, URLPattern):
            yield acc + [str(entry.pattern)]

        elif isinstance(entry, URLResolver):
            yield from self.list_urls(entry.url_patterns, acc + [str(entry.pattern)])

        yield from self.list_urls(url_pattern[1:], acc)

    def get_apps(self, include_django=False, include_third_party=False, include_project=True, as_interface=False):
        """
        Returns desired apps of the django project.

        Arguments:
            include_django (bool): should django apps be returned?
            include_project (bool): should apps from the project be returned?
            include_third_party (bool): should apps from third party be returned (not django)?
            as_interface (bool): should the return value be [AppConfig] (false) or [AppInterface] (true)?
        """
        # get all apps from application
        all_apps = list(apps.get_app_configs())

        # if all should be returned, return here
        if include_django and include_third_party and include_project:
            return all_apps

        output = []

        for app in all_apps:
            app_interface = AppInterface(app)

            # add django apps if wanted
            if include_django and self.app_defined_by_django(app):
                output.append(app_interface if as_interface else app)
                continue

            # add third party apps if wanted
            if include_third_party and self.app_defined_by_third_party(app):
                output.append(app_interface if as_interface else app)
                continue

            # add project apps if wanted
            if include_project and self.app_defined_by_project(app):
                output.append(app_interface if as_interface else app)

        return output

    def get_models(self, include_django=False, include_third_party=False, include_project=True, as_interface=False):
        output = []
        project_apps = self.get_apps(
            include_django=include_django,
            include_third_party=include_third_party,
            include_project=include_project,
            as_interface=True,
        )

        for app in project_apps:
            for model in app.get_models(as_interface=as_interface):
                output.append(model)

        return output
