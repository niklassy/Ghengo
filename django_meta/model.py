from django.apps import apps
from django.db.models.base import ModelBase

from django_meta.base import ExistsInCode
from nlp.generate.utils import to_function_name, camel_to_snake_case


class ModelWrapper(ExistsInCode):
    exists_in_code = False

    def __init__(self, name):
        class_name = ''.join(x for x in name.title() if not x.isspace())
        self.model = type(class_name, (), {})

    def get_field(self, name):
        return None

    def models_are_equal(self, model_wrapper):
        """Can be used to check if the models from this and another model wrapper are equal."""
        if not isinstance(model_wrapper, ModelWrapper) or isinstance(model_wrapper.model, ModelBase):
            return False

        return self.model.__name__ == model_wrapper.model.__name__

    @property
    def fields(self):
        return []

    @property
    def name(self):
        return self.model.__name__


class ExistingModelWrapper(ModelWrapper):
    """
    This class is a wrapper around a Django model with several functions and properties that are useful for the
    application.
    """
    exists_in_code = True

    def __init__(self, model, app):
        super().__init__(model.__name__)
        self.model = model
        self.app = app

    def models_are_equal(self, model_wrapper):
        if not isinstance(model_wrapper, ModelWrapper) or not isinstance(model_wrapper.model, ModelBase):
            return False

        return self.model == model_wrapper.model

    @classmethod
    def create_with_model(cls, model):
        app_label = model._meta.app_label

        for app in list(apps.get_app_configs()):
            if app.label == app_label:
                return ExistingModelWrapper(model, app)

        raise ValueError('No app was found.')

    @property
    def verbose_name(self):
        try:
            return str(self.model._meta.verbose_name)
        except AttributeError:
            return None

    @property
    def verbose_name_plural(self):
        try:
            return str(self.model._meta.verbose_name_plural)
        except AttributeError:
            return None

    @property
    def fields(self):
        pk_field_name = self.model._meta.pk.name
        field = self.get_field(pk_field_name)
        wrapper = ExistingModelFieldWrapper(field)
        wrapper.name = 'pk'

        return [ExistingModelFieldWrapper(field) for field in self.model._meta.get_fields()] + [wrapper]

    def get_field(self, name):
        return ExistingModelFieldWrapper(self.model._meta.get_field(name))

    @property
    def field_names(self):
        return [getattr(field, 'verbose_name', None) or field.name for field in self.fields]

    def __repr__(self):
        return 'ModelWrapper - {}'.format(self.name)


class ModelFieldWrapper(ExistsInCode):
    """
    This field can be used for a field in a model that does not exist yet.
    """
    exists_in_code = False

    def __init__(self, name):
        self.name = to_function_name(name.replace(' ', '_'))
        self.verbose_name = self.name
        self.field = self

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return self.name == other.name


class ExistingModelFieldWrapper(ModelFieldWrapper):
    exists_in_code = True

    def __init__(self, field):
        super().__init__(field.name)
        self.name = field.name
        self.field = field


class PermissionWrapper(ExistsInCode):
    """Represents a permission object from Django."""
    def __init__(self, description, model_wrapper):
        self.model_wrapper = model_wrapper
        self._description = description

    @property
    def codename(self):
        no_can = self._description.lower().replace('can', '').lstrip()
        return to_function_name(no_can.replace(' ', '_'))

    @property
    def name(self):
        return self._description

    @property
    def app_label(self):
        return self.model_label

    @property
    def model_label(self):
        return camel_to_snake_case(self.model_wrapper.name)


class ExistingPermissionWrapper(PermissionWrapper):
    exists_in_code = True

    def __init__(self, permission):
        self.permission = permission
        super().__init__(self.name, self._get_model_wrapper())

    @property
    def codename(self):
        return self.permission.codename

    @property
    def name(self):
        return self.permission.name

    @property
    def app_label(self):
        return self.permission.content_type.app_label

    def _get_model_wrapper(self):
        content_type = self.permission.content_type
        model_class = content_type.model_class()

        if model_class is None:
            return ModelWrapper(str(content_type))

        return ExistingModelWrapper.create_with_model(model=model_class)

    @property
    def model_label(self):
        return self.permission.content_type.model
