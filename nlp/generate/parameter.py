from nlp.generate.mixin import TemplateMixin
from nlp.generate.replaceable import Replaceable


class Parameter(Replaceable, TemplateMixin):
    """
    Class that represents the values that are defined by the function that it gets passed.

    Example: def foo(a, b)
    => a and b are parameters.
    """
    template = '{name}'

    def __init__(self, name):
        super().__init__()
        self.name = name

    def get_template_context(self, line_indent, indent):
        return {'name': self.name}

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return self.name == other.name
