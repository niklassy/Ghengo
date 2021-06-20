class OnAddToTestCaseListenerMixin(object):
    def on_add_to_test_case(self, test_case):
        pass


class TemplateMixin(object):
    """
    This mixin is used to convert any class into a template. The template is used for python code in this project.
    But in theory, this mixin can be used anywhere.
    """
    # TODO: move intend to __init__
    template = ''

    def get_template(self):
        return self.template

    def get_template_context(self, indent):
        return {}

    @classmethod
    def get_indent_string(cls, indent):
        return ' ' * indent

    def to_template(self, indent=0):
        return self.get_indent_string(indent) + self.get_template().format(**self.get_template_context(indent))

    def __str__(self):
        return self.to_template()
