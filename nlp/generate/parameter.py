from nlp.generate.mixin import TemplateMixin
from nlp.generate.replaceable import Replaceable
from nlp.generate.variable import Variable


class Parameter(Replaceable, TemplateMixin):
    """
    Class that represents the values that are defined by the function that it gets passed.

    Example: def foo(a, b)
    => a and b are parameters.
    """
    template = '{variable}'

    def __init__(self, name):
        super().__init__()
        self.name = name
        self.variable = Variable(name, name)

    def get_template_context(self, line_indent, at_start_of_line):
        return {'variable': self.variable}

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return self.name == other.name
