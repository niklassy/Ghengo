import importlib
import inspect

from django.urls import get_resolver, get_urlconf
from rest_framework.routers import APIRootView
from rest_framework.serializers import ModelSerializer
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet

from django_meta.base import ExistsInCode
from django_meta.model import ExistingModelWrapper
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


class ApiActionWrapper:
    """
    Every viewset can have actions which represent an action of an url. One url can have multiple actions because
    of different methods.
    """
    def __init__(self, url_pattern_wrapper, fn_name, method, url_name):
        self.fn_name = fn_name
        self.url_name = url_name
        self.method = method
        self.url_pattern_wrapper: UrlPatternWrapper = url_pattern_wrapper

    def __str__(self):
        return '{} - {} - {}'.format(self.method, self.fn_name, self.url_name)

    @property
    def serializer_cls(self):
        return lambda *args, **kwargs: None

    @property
    def model_wrapper(self):
        return self.url_pattern_wrapper.model_wrapper

    def supports_model_wrapper(self, model_wrapper):
        return self.model_wrapper and self.model_wrapper.models_are_equal(model_wrapper)


class ExistingApiActionWrapper(ApiActionWrapper):
    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False

        return all([
            self.serializer_cls == other.serializer_cls,
            self.url_pattern_wrapper == other.url_pattern_wrapper,
            self.fn_name == other.fn_name,
            self.method == other.method,
            self.url_name == other.url_name,
        ])

    @property
    def serializer_cls(self):
        url_pattern_wrapper = self.url_pattern_wrapper

        view_cls = url_pattern_wrapper.view_cls
        try:
            view = view_cls(request=None, format_kwarg=None, action=self.fn_name)
        except TypeError:
            return None

        try:
            return view.get_serializer_class()
        except Exception:
            return None

    @property
    def model_wrapper(self):
        if not issubclass(self.serializer_cls, ModelSerializer):
            return None

        return ExistingModelWrapper.create_with_model(self.serializer_cls.Meta.model)


class UrlPatternWrapper(object):
    def __init__(self, model_wrapper):
        self.model_wrapper = model_wrapper

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False

        return self.reverse_name == other.reverse_name

    def key_exists_in_route_kwargs(self, key):
        """
        Check if a given key exists in the kwargs of the url. By default only pk and id are given in urls.
        """
        return key == 'pk' or key == 'id'

    def get_all_actions_for_model_wrapper(self, model_wrapper):
        """Returns all the actions that support the model wrapper"""
        return []

    def supports_model_wrapper(self, model_wrapper):
        """
        Check if this url pattern supports the given model wrapper.
        """
        return self.model_wrapper.models_are_equal(model_wrapper)

    @property
    def is_represented_by_view_set(self):
        """
        Check if this url is represented by a view set. By default set to true to continue normally.
        """
        return True

    @property
    def methods(self):
        """
        Returns all methods that this wrapper supports. By default, all of them are returned.
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
        return '{}-{}'.format(self.model_wrapper.name.lower(), 'detail')

    def get_serializer_class(self, action_wrapper):
        """
        Returns the class of the serializer for a given method. By default None is returned.

        :argument for_method - one of Methods
        """
        return None


class ExistingUrlPatternWrapper(UrlPatternWrapper):
    def __init__(self, url_pattern):
        self.url_pattern = url_pattern
        self._view_set_cached = None
        self._api_view_cached = None
        self._view_cls = None
        self._view_set_determined = False
        self._api_view_determined = False

        self._api_actions = None
        self._methods = None

        super().__init__(model_wrapper=None)

    def key_exists_in_route_kwargs(self, key):
        """
        Function that checks if a given key exists in the route_kwargs.
        """
        return key in self._route_kwargs

    def supports_model_wrapper(self, model_wrapper):
        """Checks if this instance supports the given model wrapper."""
        return any([model_wrapper.models_are_equal(mw) for mw in self._models])

    def get_all_actions_for_model_wrapper(self, model_wrapper):
        """Returns all actions that support the given model wrapper."""
        if not self.supports_model_wrapper(model_wrapper):
            return []

        output = []
        for action in self.api_actions:
            if action.supports_model_wrapper(model_wrapper):
                output.append(action)

        return output

    @property
    def reverse_name(self):
        """
        Returns the reverse name for the url that can be used via reverse(<name>).
        """
        return self.url_pattern.name

    @property
    def view_cls(self):
        if self._view_cls is None:
            self._view_cls = self._get_view_cls()
        return self._view_cls

    @property
    def _route_kwargs(self):
        resolver = get_resolver(get_urlconf())

        try:
            return resolver.reverse_dict[self.reverse_name][0][0][1]
        except IndexError:
            return []

    @property
    def _models(self):
        """Returns all models that this url can possibly reference (in serializers)."""
        return [action.model_wrapper for action in self.api_actions]

    def _get_api_actions(self) -> [ApiActionWrapper]:
        """
        Returns all action wrappers that the url supports.
        """
        if self._api_view is not None:
            actions = self._api_view.get_all_actions()
        elif self._view_set is not None:
            actions = self._view_set.get_all_actions()
        else:
            actions = []

        action_wrappers = []
        for fn_name, method, url_name in actions:
            # filter any actions that have a method or url name that does not fit
            if method in self.methods and url_name == self.reverse_url_name:
                action_wrappers.append(
                    ExistingApiActionWrapper(
                        url_pattern_wrapper=self,
                        fn_name=fn_name,
                        method=method,
                        url_name=url_name,
                    )
                )

        return action_wrappers

    @property
    def api_actions(self) -> [ApiActionWrapper]:
        """
        Returns all api actions for the view set.
        """
        if self._api_actions is None:
            self._api_actions = self._get_api_actions()
        return self._api_actions

    def get_serializer_class(self, action_wrapper):
        """
        Returns the serializer class that is responsible for the url.
        """
        view_cls = self.view_cls
        view = view_cls(request=None, format_kwarg=None, action=action_wrapper.fn_name)
        return view.get_serializer_class()

    def _get_methods(self):
        """Private method that is used to receive all methods that this url supports."""
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

    @property
    def methods(self):
        """
        Returns all the methods that the api view/ view set supports.
        """
        if self._methods is None:
            self._methods = self._get_methods()
        return self._methods

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
            view_cls = self.view_cls

            if not inspect.isclass(view_cls):
                self._api_view_cached = None
            else:
                is_valid_api_view = issubclass(view_cls, APIView) and view_cls != APIRootView
                is_view_set = issubclass(view_cls, GenericViewSet)

                if is_valid_api_view and not is_view_set:
                    self._api_view_cached = ApiViewWrapper(view_cls(request=None, format_kwargs=None))
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
            view_cls = self.view_cls

            if view_cls and inspect.isclass(view_cls) and issubclass(view_cls, GenericViewSet):
                self._view_set_cached = ViewSetWrapper(view_cls(request=None, format_kwarg=None))
            else:
                self._view_set_cached = None

            self._view_set_determined = True

        return self._view_set_cached


class ApiViewWrapper(object):
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


class ViewSetWrapper(object):
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


class ApiFieldWrapper(ExistsInCode):
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


class ExistingApiFieldWrapper(ApiFieldWrapper):
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
