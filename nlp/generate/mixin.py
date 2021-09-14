class OnAddToTestCaseListenerMixin(object):
    """
    This mixin is used to keep of children and notify them as soon as they are added to a test case. This only works
    if all the parents of the given instance are subclasses of this class.
    """
    def __init__(self):
        super().__init__()

        self.test_case = None

    def get_children(self):
        raise NotImplementedError()

    def on_add_to_test_case(self, test_case):
        self.test_case = test_case

        for child in self.get_children():
            if isinstance(child, OnAddToTestCaseListenerMixin):
                child.on_add_to_test_case(test_case)


class TemplateMixin(object):
    """
    This mixin is used to convert any class into a template. The template is used for python code in this project.
    But in theory, this mixin can be used anywhere.
    """
    template = ''

    def get_template(self):
        return self.template

    def get_template_context(self, line_indent, at_start_of_line):
        """
        Returns the context that is injected into the template.

        :argument: line_indent = stands for the current indentation of the line in the code
        :argument: at_start_of_line = indicates that this instance will be at the start of a line in the code
        """
        return {}

    @classmethod
    def get_indent_string(cls, indent):
        """
        Helper function to return an indent string.

        :argument: line_indent (int) = number of indentations
        """
        return ' ' * indent

    def to_template(self, line_indent=0, at_start_of_line=True):
        """
        This function will return the filled in template. It will also handle indentation.

        :argument: line_indent = stands for the current indentation of the line in the code
        :argument: at_start_of_line = indicates that this instance will be at the start of a line in the code
        """
        assert isinstance(at_start_of_line, bool)
        indent = self.get_indent_string(line_indent) if at_start_of_line else ''

        return indent + self.get_template().format(
            **self.get_template_context(line_indent, at_start_of_line)
        )

    def __str__(self):
        return self.to_template()
