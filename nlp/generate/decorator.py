from nlp.generate.mixin import TemplateMixin, OnAddToTestCaseListenerMixin
from nlp.generate.replaceable import Replaceable


class Decorator(Replaceable, TemplateMixin, OnAddToTestCaseListenerMixin):
    template = '@{decorator_name}{arguments}'

    def __init__(self, name, arguments=None):
        super().__init__()
        self.name = name
        self.arguments = arguments or []

    def get_children(self):
        return self.arguments

    def get_template_context(self, line_indent, at_start_of_line):
        if len(self.arguments) > 0:
            arguments = '({})'.format(
                ', '.join([argument.to_template(line_indent, at_start_of_line=False) for argument in self.arguments]))
        else:
            arguments = ''

        return {
            'decorator_name': self.name,
            'arguments': arguments,
        }

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return self.name == other.name
