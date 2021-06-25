from django_meta.model import ModelInterface


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
