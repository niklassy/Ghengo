import importlib
import inspect

from django.urls import get_resolver, get_urlconf
from rest_framework.routers import APIRootView
from rest_framework.serializers import ModelSerializer
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet

from django_meta.model import ModelAdapter
from nlp.generate.utils import to_function_name


class Methods:
    GET = 'get'
    POST = 'post'
    PATCH = 'patch'
    PUT = 'put'
    DELETE = 'delete'


class UrlPatternAdapter(object):
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
    def model_adapter(self):
        view_cls = self._get_view_cls()
        view = view_cls(request=None, format_kwarg=None)
        try:
            serializer_cls = view.get_serializer_class()
        except Exception:
            return None

        if not issubclass(serializer_cls, ModelSerializer):
            return None

        return ModelAdapter.create_with_model(serializer_cls.Meta.model)

    @property
    def route_kwargs(self):
        resolver = get_resolver(get_urlconf())

        try:
            return resolver.reverse_dict[self.reverse_name][0][0][1]
        except IndexError:
            return []

    @property
    def view_set_name(self):
        return self.reverse_name.split('-')[0]

    @property
    def url_name(self):
        return '-'.join(self.reverse_name.split('-')[1:])

    @property
    def all_api_actions(self):
        if self.api_view is not None:
            return self.api_view.get_all_actions()

        return self.view_set.get_all_actions()

    def get_serializer_class(self, for_method):
        for fn_name, method, url_name in self.all_api_actions:
            if for_method == method and url_name == self.url_name:
                view_cls = self._get_view_cls()
                view = view_cls(request=None, format_kwarg=None, action=fn_name)
                return view.get_serializer_class()
        return None

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
            view_cls = self._get_view_cls()

            is_valid_api_view = issubclass(view_cls, APIView) and view_cls != APIRootView
            is_view_set = issubclass(view_cls, GenericViewSet)

            if inspect.isclass(view_cls) and is_valid_api_view and not is_view_set:
                self._api_view = ApiViewAdapter(view_cls(request=None, format_kwargs=None))
            else:
                self._api_view = None

            self._api_view_determined = True
        return self._api_view

    @property
    def view_set(self):
        if self._view_set_determined is False:
            view_cls = self._get_view_cls()

            if inspect.isclass(view_cls) and issubclass(view_cls, GenericViewSet):
                self._view_set = ViewSetAdapter(view_cls(request=None, format_kwarg=None))
            else:
                self._view_set = None

            self._view_set_determined = True

        return self._view_set


class ApiViewAdapter(object):
    def __init__(self, api_view):
        self.api_view = api_view

    def get_all_actions(self):
        possible_actions = [
            ('get', Methods.GET, ''),
            ('post', Methods.POST, ''),
            ('patch', Methods.PATCH, ''),
            ('put', Methods.PUT, ''),
            ('delete', Methods.DELETE, ''),
        ]

        actions = []
        for fn_name, method, url_name in possible_actions:
            if hasattr(self.api_view, fn_name):
                actions.append((fn_name, method, url_name))

        return actions


class ViewSetAdapter(object):
    def __init__(self, view_set):
        self.view_set = view_set

    def get_all_actions(self):
        extra_actions = [
            extra_action for extra_action in self.view_set.get_extra_actions()
        ]
        default_actions = [
            ('list', Methods.GET, 'list'),
            ('retrieve', Methods.GET, 'detail'),
            ('partial_update', Methods.PATCH, 'detail'),
            ('update', Methods.PUT, 'detail'),
            ('create', Methods.POST, 'detail'),
            ('destroy', Methods.DELETE, 'detail'),
        ]

        actions = []
        for default_action, method, url_name in default_actions:
            if hasattr(self.view_set, default_action):
                actions.append((default_action, method, url_name))

        for extra_action in extra_actions:
            for method in extra_action.mapping:
                actions.append((extra_action.url_path, method, extra_action.url_name))

        return actions


class AbstractApiFieldAdapter(object):
    exists_in_code = False

    def __init__(self, name):
        self.name = to_function_name(name)
        self.source = self.name
        self.verbose_name = self.name
        self.read_only = False
        self.model_field = None

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return self.name == other.name


class ApiFieldAdapter(AbstractApiFieldAdapter):
    exists_in_code = True

    def __init__(self, api_field):
        super().__init__(api_field.source)
        self.field = api_field
        self.name = api_field.source
        self.read_only = api_field.read_only

        try:
            self.model_field = api_field.model_field
        except AttributeError:
            pass
