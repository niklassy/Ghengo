from nlp.generate.mixin import TemplateMixin, OnAddToTestCaseListenerMixin


class Decorator(TemplateMixin, OnAddToTestCaseListenerMixin):
    template = '@{decorator_name}{arguments}'

    def __init__(self, name, arguments=None):
        self.name = name
        self.arguments = arguments or []

    def get_template_context(self, indent):
        if len(self.arguments) > 0:
            arguments = '({})'.format(', '.join([argument.to_template(indent) for argument in self.arguments]))
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
