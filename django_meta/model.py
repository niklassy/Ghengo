from django.apps import apps

from nlp.generate.utils import to_function_name


class ModelInterface(object):
    """
    This class is a wrapper around a Django model with several functions and properties that are useful for the
    application.
    """
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
    """
    This interface can be used for a Model that actually does not exist yet.
    """
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
    """
    This field can be used for a field in a model that does not exist yet.
    """
    def __init__(self, name):
        self.name = to_function_name(name)
        self.verbose_name = self.name

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return self.name == other.name
