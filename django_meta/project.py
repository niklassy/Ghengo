import importlib

from django.apps import apps
from django.urls import URLPattern, URLResolver, get_resolver

from django_meta.app import AppWrapper
from django_meta.setup import setup_django


class DjangoProject(object):
    class RegisterKeys:
        THIRD_PARTY = 'third_party'
        DJANGO = 'django'
        FROM_APP = 'from_app'

    def __init__(self, settings_path):
        self.settings = importlib.import_module(settings_path)

        # django needs to know where the settings are, so set it in the env and setup django afterwards
        setup_django(settings_path)

        self._urls = None

        self._apps_cached = False
        self._app_dict = {
            self.RegisterKeys.THIRD_PARTY: [],
            self.RegisterKeys.DJANGO: [],
            self.RegisterKeys.FROM_APP: [],
        }

    def get_reverse_keys(self):
        """Returns all keys that are used in the project that can be used via reverse"""
        return get_resolver().reverse_dict.keys()

    def _cache_app(self, app, third_party=False, from_django=False):
        """Cache an app for later usage."""
        if third_party:
            key = self.RegisterKeys.THIRD_PARTY
        elif from_django:
            key = self.RegisterKeys.DJANGO
        else:
            key = self.RegisterKeys.FROM_APP

        app_list = self._app_dict[key]
        if app not in app_list:
            app_list.append(app)

    def _find_and_cache_apps(self):
        all_apps = list(apps.get_app_configs())

        for app in all_apps:
            app_wrapper = AppWrapper(app, self)

            if app_wrapper.defined_by_django:
                self._cache_app(app_wrapper, from_django=True)
                continue

            # add third party apps if wanted
            if app_wrapper.defined_by_third_party:
                self._cache_app(app_wrapper, third_party=True)
                continue

            # add project apps if wanted
            if app_wrapper.defined_by_project:
                self._cache_app(app_wrapper)

        self._apps_cached = True

    @property
    def urls(self):
        if self._urls is None:
            self._urls = self._list_urls(as_pattern=True)
        return self._urls

    def _list_urls(self, url_pattern=None, url_list=None, as_pattern=False):
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
                    self._list_urls(url_entry.url_patterns, url_list, as_pattern)
                else:
                    for pattern in url_entry.url_patterns:
                        url_list.append(self._list_urls([pattern], [str(url_entry.pattern)], as_pattern))

        return url_list

    def get_apps(self, include_django=False, include_third_party=False, include_project=True, as_wrapper=False):
        """
        Returns desired apps of the django project.

        Arguments:
            include_django (bool): should django apps be returned?
            include_project (bool): should apps from the project be returned?
            include_third_party (bool): should apps from third party be returned (not django)?
            as_wrapper (bool): should the return value be [AppConfig] (false) or [AppWrapper] (true)?
        """
        if self._apps_cached is False:
            self._find_and_cache_apps()

        output = []

        if include_django:
            output += self._app_dict[self.RegisterKeys.DJANGO]

        if include_third_party:
            output += self._app_dict[self.RegisterKeys.THIRD_PARTY]

        if include_project:
            output += self._app_dict[self.RegisterKeys.FROM_APP]

        if as_wrapper:
            return output

        return [wrapper.app for wrapper in output]

    def get_models(self, include_django=False, include_third_party=False, include_project=True, as_wrapper=False):
        """
        Returns all the models that are used in the project. The output can be filtered.

        Arguments:
            include_django (bool): include django models?
            include_project (bool): include models from the project itself?
            include_third_party (bool): include third party models?
            as_wrapper (bool): return as [ModelWrapper]?
        """
        output = []
        project_apps = self.get_apps(
            include_django=include_django,
            include_third_party=include_third_party,
            include_project=include_project,
            as_wrapper=True,
        )

        for app in project_apps:
            for model in app.get_models(as_wrapper=as_wrapper):
                output.append(model)

        return output
