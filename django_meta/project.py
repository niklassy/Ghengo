import importlib
import os

from django.apps import apps
from django import setup
from django.urls import URLPattern, URLResolver, get_resolver


class ModelInterface(object):
    def __init__(self, model, app):
        self.model = model
        self.app = app

    @property
    def verbose_name(self):
        return str(self.model._meta.verbose_name) or self.model.__name__

    @property
    def fields(self):
        return list(self.model._meta.get_fields())

    def get_field(self, name):
        return self.model._meta.get_field(name)

    @property
    def field_names(self):
        return [field.verbose_name or field.name for field in self.fields]


class AppInterface(object):
    def __init__(self, app, project):
        self.app = app
        self.project = project

    def get_models(self, as_interface=False):
        output = []

        for model in self.app.get_models():
            if as_interface:
                model = ModelInterface(model, self)
            output.append(model)

        return output

    @property
    def defined_by_project(self):
        return self.project.settings.BASE_DIR in self.app.path

    @property
    def defined_by_django(self):
        return self.app.name.startswith('django.')

    @property
    def defined_by_third_party(self):
        return not self.defined_by_django and not self.defined_by_project


class DjangoProject(object):
    def __init__(self, settings_path):
        self.settings = importlib.import_module(settings_path)

        # django needs to know where the settings are, so set it in the env and setup django afterwards
        os.environ['DJANGO_SETTINGS_MODULE'] = settings_path
        setup()

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
            app_interface = AppInterface(app, self)

            # add django apps if wanted
            if include_django and app_interface.defined_by_django:
                output.append(app_interface if as_interface else app)
                continue

            # add third party apps if wanted
            if include_third_party and app_interface.defined_by_third_party:
                output.append(app_interface if as_interface else app)
                continue

            # add project apps if wanted
            if include_project and app_interface.defined_by_project:
                output.append(app_interface if as_interface else app)

        return output

    def get_models(self, include_django=False, include_third_party=False, include_project=True, as_interface=False):
        """
        Returns all the models that are used in the project. The output can be filtered.

        Arguments:
            include_django (bool): include django models?
            include_project (bool): include models from the project itself?
            include_third_party (bool): include third party models?
            as_interface (bool): return as [ModelInterface]?
        """
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
