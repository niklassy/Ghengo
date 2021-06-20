class OnAddToTestCaseListenerMixin(object):
    def on_add_to_test_case(self, test_case):
        pass


class TemplateMixin(object):
    """
    This mixin is used to convert any class into a template. The template is used for python code in this project.
    But in theory, this mixin can be used anywhere.
    """
    template = ''

    def __init__(self):
        self.indent = 0

    def get_template(self):
        return self.template

    def get_template_context(self, parent_intend):
        return {}

    @classmethod
    def get_indent_string(cls, indent):
        return ' ' * indent

    def to_template(self, parent_indent=0):
        return self.get_indent_string(self.indent) + self.get_template().format(
            **self.get_template_context(parent_indent)
        )

    def __str__(self):
        return self.to_template()
