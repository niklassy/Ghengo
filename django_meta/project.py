import importlib
import inspect
import os

from django.apps import apps
from django import setup
from django.urls import URLPattern, URLResolver, get_resolver

from nlp.generate.utils import to_function_name


class UrlPatternInterface(object):
    def __init__(self, url_pattern):
        self.url_pattern = url_pattern
        self._view_set = None
        self._api_view = None
        self._view_set_determined = False
        self._api_view_determined = False

    @property
    def reverse_name(self):
        return self.url_pattern.name

    @property
    def view_set_name(self):
        return self.reverse_name.split('-')[0]

    @property
    def url_name(self):
        return '-'.join(self.reverse_name.split('-')[1:])

    @property
    def methods(self):
        if self.view_set is None and self.api_view is None:
            return []

        methods = []
        if self.api_view is not None:
            for _, method, url_name in self.api_view.get_all_actions():
                if method not in methods:
                    methods.append(method)

            return methods

        for _, method, url_name in self.view_set.get_all_actions():
            if url_name == self.url_name and method not in methods:
                methods.append(method)

        return methods

    def _get_view_cls(self):
        lookup_str = self.url_pattern.lookup_str

        full_name_as_list = lookup_str.split('.')
        full_name_as_list.reverse()

        view_name = []
        view_path = lookup_str.split('.')
        module = None

        for lookup_part in full_name_as_list:
            view_name.append(lookup_part)
            view_path = view_path[:-1]

            try:
                module = importlib.import_module('.'.join(view_path))
                break
            except ModuleNotFoundError:
                continue
        view_name.reverse()
        return getattr(module, view_name[0])

    @property
    def api_view(self):
        if self._api_view_determined is False:
            from rest_framework.views import APIView
            from rest_framework.viewsets import GenericViewSet
            from rest_framework.routers import APIRootView
            view_cls = self._get_view_cls()

            if inspect.isclass(view_cls) and issubclass(view_cls, APIView) and view_cls != APIRootView and not issubclass(view_cls, GenericViewSet):
                self._api_view = ApiViewInterface(view_cls(request=None, format_kwargs=None))
            else:
                self._api_view = None

            self._api_view_determined = True
        return self._api_view

    @property
    def view_set(self):
        if self._view_set_determined is False:
            from rest_framework.viewsets import GenericViewSet
            view_cls = self._get_view_cls()

            if inspect.isclass(view_cls) and issubclass(view_cls, GenericViewSet):
                self._view_set = ViewSetInterface(view_cls(request=None, format_kwarg=None))
            else:
                self._view_set = None

            self._view_set_determined = True

        return self._view_set


class ApiViewInterface(object):
    def __init__(self, api_view):
        self.api_view = api_view

    @property
    def methods(self):
        return [method.lower() for method in self.api_view.allowed_methods if method.lower() != 'options']

    def get_all_actions(self):
        possible_actions = [
            ('get', 'get', ''),
            ('post', 'post', ''),
            ('patch', 'patch', ''),
            ('put', 'put', ''),
        ]

        actions = []
        for fn_name, method, url_name in possible_actions:
            if hasattr(self.api_view, fn_name):
                actions.append((fn_name, method, url_name))

        return actions


class ViewSetInterface(object):
    def __init__(self, view_set):
        self.view_set = view_set

    def get_all_actions(self):
        extra_actions = [
            extra_action for extra_action in self.view_set.get_extra_actions()
        ]
        default_actions = [
            ('list', 'get', 'list'),
            ('retrieve', 'get', 'detail'),
            ('partial_update', 'patch', 'detail'),
            ('update', 'put', 'detail'),
            ('create', 'post', 'detail'),
        ]

        actions = []
        for default_action, method, url_name in default_actions:
            if hasattr(self.view_set, default_action):
                actions.append((default_action, method, url_name))

        for extra_action in extra_actions:
            for method in extra_action.mapping:
                actions.append((extra_action.url_path, method, extra_action.url_name))

        return actions


class ModelInterface(object):
    def __init__(self, model, app):
        self.model = model
        self.app = app

    @classmethod
    def create_with_model(cls, model):
        app_label = model._meta.app_label

        for app in list(apps.get_app_configs()):
            if app.label == app_label:
                return ModelInterface(model, app)

        raise ValueError('No app was found.')

    @property
    def verbose_name(self):
        try:
            return str(self.model._meta.verbose_name)
        except AttributeError:
            return None

    @property
    def name(self):
        return self.model.__name__

    @property
    def fields(self):
        return list(self.model._meta.get_fields())

    def get_field(self, name):
        return self.model._meta.get_field(name)

    @property
    def field_names(self):
        return [getattr(field, 'verbose_name', None) or field.name for field in self.fields]

    def __repr__(self):
        return 'ModelInterface - {}'.format(self.name)


class AbstractModelInterface(ModelInterface):
    def __init__(self, name):
        # convert to pascal case
        class_name = ''.join(x for x in name.title() if not x.isspace())
        super().__init__(type(class_name, (), {}), None)

    def get_field(self, name):
        return None

    @property
    def fields(self):
        return []


class AbstractModelField(object):
    def __init__(self, name):
        self.name = to_function_name(name)
        self.verbose_name = self.name

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return self.name == other.name


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
        print('Setting up Django....')
        os.environ['DJANGO_SETTINGS_MODULE'] = settings_path
        setup()
        print('Finished setting up Django!')

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
