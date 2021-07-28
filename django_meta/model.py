from django.apps import apps
from django.db.models import Model

from django_meta.base import ExistsInCode
from nlp.generate.utils import to_function_name


class AbstractModelAdapter(ExistsInCode):
    exists_in_code = False

    def __init__(self, name):
        class_name = ''.join(x for x in name.title() if not x.isspace())
        self.model = type(class_name, (), {})

    def get_field(self, name):
        return None

    def models_are_equal(self, model_adapter):
        """Can be used to check if the models from this and another model adapter are equal."""
        if not isinstance(model_adapter, AbstractModelAdapter) or isinstance(model_adapter.model, Model):
            return False

        return self.model.__name__ == model_adapter.model.__name__

    @property
    def fields(self):
        return []

    @property
    def name(self):
        return self.model.__name__


class ModelAdapter(AbstractModelAdapter):
    """
    This class is a wrapper around a Django model with several functions and properties that are useful for the
    application.
    """
    exists_in_code = True

    def __init__(self, model, app):
        super().__init__(model.__name__)
        self.model = model
        self.app = app

    def models_are_equal(self, model_adapter):
        if not isinstance(model_adapter, AbstractModelAdapter) or not isinstance(model_adapter.model, Model):
            return False

        return self.model == model_adapter.model

    @classmethod
    def create_with_model(cls, model):
        app_label = model._meta.app_label

        for app in list(apps.get_app_configs()):
            if app.label == app_label:
                return ModelAdapter(model, app)

        raise ValueError('No app was found.')

    @property
    def verbose_name(self):
        try:
            return str(self.model._meta.verbose_name)
        except AttributeError:
            return None

    @property
    def fields(self):
        return [ModelFieldAdapter(field) for field in self.model._meta.get_fields()]

    def get_field(self, name):
        return ModelFieldAdapter(self.model._meta.get_field(name))

    @property
    def field_names(self):
        return [getattr(field, 'verbose_name', None) or field.name for field in self.fields]

    def __repr__(self):
        return 'ModelAdapter - {}'.format(self.name)


class AbstractModelFieldAdapter(ExistsInCode):
    """
    This field can be used for a field in a model that does not exist yet.
    """
    exists_in_code = False

    def __init__(self, name):
        self.name = to_function_name(name)
        self.verbose_name = self.name
        self.field = self

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return self.name == other.name


class ModelFieldAdapter(AbstractModelFieldAdapter):
    exists_in_code = True

    def __init__(self, field):
        super().__init__(field.name)
        self.name = field.name
        self.field = field
