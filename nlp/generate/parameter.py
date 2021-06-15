from nlp.generate.mixin import TemplateMixin


class Parameter(TemplateMixin):
    """
    Class that represents the values that are defined by the function that it gets passed.

    Example: def foo(a, b)
    => a and b are parameters.
    """
    template = '{name}'

    def __init__(self, name):
        self.name = name

    def get_template_context(self, indent):
        return {'name': self.name}

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return self.name == other.name
