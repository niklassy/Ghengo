from nlp.generate.argument import Argument
from nlp.generate.decorator import Decorator
from nlp.generate.parameter import Parameter
from nlp.generate.settings import INDENT_SPACES
from nlp.generate.suite import Import


class PyTestMarkDecorator(Decorator):
    """A Pytest mark decorator (pytest.mark.XXX)."""
    def __init__(self, name, arguments=None):
        super().__init__('pytest.mark.{}'.format(name), arguments)

    def on_add_to_test_case(self, test_case):
        test_case.test_suite.add_import(Import('pytest'))


class PyTestParametrizeDecorator(PyTestMarkDecorator):
    def __init__(self, argument_names, argument_values):
        self.argument_names_raw = argument_names
        arguments = []
        self.argument_names = Argument(', '.join(argument_names))
        if self.argument_names:
            arguments.append(self.argument_names)

        self.argument_values = Argument(argument_values)
        if self.argument_values:
            arguments.append(self.argument_values)

        super().__init__('parametrize', arguments)

    def get_template_context(self, indent):
        context = super().get_template_context(indent)
        # since parametrize decorators can be quite long, add some line breaks here
        if len(self.arguments) > 0:
            argument_values = [argument.to_template(indent + INDENT_SPACES) for argument in self.arguments]
            arguments = '(\n{}\n)'.format(',\n'.join(argument_values))
        else:
            arguments = ''

        context['arguments'] = arguments
        return context

    def on_add_to_test_case(self, test_case):
        super().on_add_to_test_case(test_case)

        for argument_name in self.argument_names_raw:
            try:
                test_case.add_parameter(Parameter(argument_name))
            except test_case.ParameterAlreadyPresent:
                pass


class DjangoDBDecorator(PyTestMarkDecorator):
    def __init__(self):
        super().__init__('django_db')

