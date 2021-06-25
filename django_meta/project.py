import importlib

from django.apps import apps
from django.urls import URLPattern, URLResolver, get_resolver

from django_meta.app import AppInterface
from django_meta.setup import setup_django


class DjangoProject(object):
    def __init__(self, settings_path):
        self.settings = importlib.import_module(settings_path)

        # django needs to know where the settings are, so set it in the env and setup django afterwards
        setup_django(settings_path)

    def get_reverse_keys(self):
        """Returns all keys that are used in the project that can be used via reverse"""
        return get_resolver().reverse_dict.keys()

    def list_urls(self, url_pattern=None, url_list=None, as_pattern=False):
        """
        Returns all urls that are available in the project.

        Returns:
            [[str]]
        """
        if url_pattern is None:
            url_pattern = __import__(self.settings.ROOT_URLCONF, {}, {}, ['']).urlpatterns

        if url_list is None:
            url_list = []

        if not url_pattern:
            return

        for url_entry in url_pattern:
            if isinstance(url_entry, URLPattern):
                if as_pattern:
                    url_list.append(url_entry)
                else:
                    url_list.append(str(url_entry.pattern))

            elif isinstance(url_entry, URLResolver):
                if as_pattern:
                    self.list_urls(url_entry.url_patterns, url_list, as_pattern)
                else:
                    for pattern in url_entry.url_patterns:
                        url_list.append(self.list_urls([pattern], [str(url_entry.pattern)], as_pattern))

        return url_list

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
