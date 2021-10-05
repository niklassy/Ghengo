from django_meta.model import ExistingModelWrapper


class AppWrapper(object):
    def __init__(self, app, project):
        self.app = app
        self.project = project

        self._models = None

    def get_models(self, as_wrapper=False):
        if self._models is None:
            self._models = [ExistingModelWrapper(model, self) for model in self.app.get_models()]

        if as_wrapper:
            return self._models

        return [wrapper.model for wrapper in self._models]

    @property
    def defined_by_project(self):
        return self.project.settings.BASE_DIR in self.app.path

    @property
    def defined_by_django(self):
        return self.app.name.startswith('django.')

    @property
    def defined_by_third_party(self):
        return not self.defined_by_django and not self.defined_by_project
