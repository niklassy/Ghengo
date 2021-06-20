class OnAddToTestCaseListenerMixin(object):
    def on_add_to_test_case(self, test_case):
        pass


class TemplateMixin(object):
    """
    This mixin is used to convert any class into a template. The template is used for python code in this project.
    But in theory, this mixin can be used anywhere.
    """
    template = ''

    def get_template(self):
        return self.template

    def get_template_context(self, line_indent, indent):
        return {}

    @classmethod
    def get_indent_string(cls, indent):
        return ' ' * indent

    def to_template(self, line_indent=0, indent=0):
        return self.get_indent_string(indent) + self.get_template().format(
            **self.get_template_context(line_indent, indent)
        )

    def __str__(self):
        return self.to_template()
