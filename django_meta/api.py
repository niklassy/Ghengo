import importlib
import inspect

from django.urls import get_resolver, get_urlconf
from rest_framework.routers import APIRootView
from rest_framework.serializers import ModelSerializer
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet

from django_meta.base import ExistsInCode
from django_meta.model import ModelAdapter
from nlp.generate.utils import to_function_name


class Methods:
    GET = 'get'
    POST = 'post'
    PATCH = 'patch'
    PUT = 'put'
    DELETE = 'delete'

    @classmethod
    def get_all(cls):
        return [cls.GET, cls.PUT, cls.POST, cls.DELETE, cls.PATCH]


class AbstractUrlPatternAdapter(object):
    def __init__(self, model_adapter):
        self.model_adapter = model_adapter

    def key_exists_in_route_kwargs(self, key):
        """
        Check if a given key exists in the kwargs of the url. By default only pk and id are given in urls.
        """
        return key == 'pk' or key == 'id'

    @property
    def is_represented_by_view_set(self):
        """
        Check if this url is represented by a view set. By default set to true to continue normally.
        """
        return True

    @property
    def methods(self):
        """
        Returns all methods that this adapter supports. By default, all of them are returned.
        """
        return Methods.get_all()

    def method_is_supported(self, method):
        """Checks if a given method is supported by the url."""
        return method in self.methods

    @property
    def reverse_url_name(self):
        """Returns the part of the reverse name that represents the url"""
        return '-'.join(self.reverse_name.split('-')[1:])

    @property
    def reverse_viewset_name(self):
        """Returns the part of the reverse name that represents the viewset"""
        return self.reverse_name.split('-')[0]

    @property
    def reverse_name(self):
        """Get a guessed reverse name for the pattern."""
        return '{}-{}'.format(self.model_adapter.name.lower(), 'detail')

    def get_serializer_class(self, for_method):
        """
        Returns the class of the serializer for a given method. By default None is returned.

        :argument for_method - one of Methods
        """
        return None


class UrlPatternAdapter(AbstractUrlPatternAdapter):
    def __init__(self, url_pattern):
        self.url_pattern = url_pattern
        self._view_set_cached = None
        self._api_view_cached = None
        self._view_set_determined = False
        self._api_view_determined = False
        super().__init__(model_adapter=self._get_model_adapter())

    def key_exists_in_route_kwargs(self, key):
        """
        Function that checks if a given key exists in the route_kwargs.
        """
        return key in self._route_kwargs

    @property
    def reverse_name(self):
        """
        Returns the reverse name for the url that can be used via reverse(<name>).
        """
        return self.url_pattern.name

    def _get_model_adapter(self):
        view_cls = self._get_view_cls()
        try:
            view = view_cls(request=None, format_kwarg=None)
        except TypeError:
            return None

        try:
            serializer_cls = view.get_serializer_class()
        except Exception:
            return None

        if not issubclass(serializer_cls, ModelSerializer):
            return None

        return ModelAdapter.create_with_model(serializer_cls.Meta.model)

    @property
    def _route_kwargs(self):
        resolver = get_resolver(get_urlconf())

        try:
            return resolver.reverse_dict[self.reverse_name][0][0][1]
        except IndexError:
            return []

    @property
    def _all_api_actions(self):
        """
        Returns all api actions for the view set.
        """
        if self._api_view is not None:
            return self._api_view.get_all_actions()

        return self._view_set.get_all_actions()

    def get_serializer_class(self, for_method):
        """
        Returns the serializer class that is responsible for the url.
        """
        for fn_name, method, url_name in self._all_api_actions:
            if for_method == method and url_name == self.reverse_url_name:
                view_cls = self._get_view_cls()
                view = view_cls(request=None, format_kwarg=None, action=fn_name)
                return view.get_serializer_class()
        return None

    @property
    def methods(self):
        """
        Returns all the methods that the api view/ view set supports.
        """
        if self._view_set is None and self._api_view is None:
            return []

        methods = []
        if self._api_view is not None:
            for _, method, url_name in self._api_view.get_all_actions():
                if method not in methods:
                    methods.append(method)

            return methods

        for _, method, url_name in self._view_set.get_all_actions():
            if url_name == self.reverse_url_name and method not in methods:
                methods.append(method)

        return methods

    def _get_view_cls(self):
        """
        Returns the actual view class for the url.
        """
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
    def _api_view(self):
        """
        Returns the api view that belongs to the url pattern.
        """
        if self._api_view_determined is False:
            view_cls = self._get_view_cls()

            is_valid_api_view = issubclass(view_cls, APIView) and view_cls != APIRootView
            is_view_set = issubclass(view_cls, GenericViewSet)

            if inspect.isclass(view_cls) and is_valid_api_view and not is_view_set:
                self._api_view_cached = ApiViewAdapter(view_cls(request=None, format_kwargs=None))
            else:
                self._api_view_cached = None

            self._api_view_determined = True
        return self._api_view_cached

    @property
    def is_represented_by_view_set(self):
        return self._view_set is not None

    @property
    def _view_set(self):
        """
        Returns the view set that represents the url pattern. May be None
        """
        if self._view_set_determined is False:
            view_cls = self._get_view_cls()

            if inspect.isclass(view_cls) and issubclass(view_cls, GenericViewSet):
                self._view_set_cached = ViewSetAdapter(view_cls(request=None, format_kwarg=None))
            else:
                self._view_set_cached = None

            self._view_set_determined = True

        return self._view_set_cached


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
                actions.append((extra_action.url_path, method, extra_action.mapping[method]))

        return actions


class AbstractApiFieldAdapter(ExistsInCode):
    exists_in_code = False

    def __init__(self, name):
        self.name = to_function_name(name)
        self.source = self.name
        self.verbose_name = self.name
        self.read_only = False
        self.model_field = None
        self.field = self

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
