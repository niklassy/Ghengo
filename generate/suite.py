from generate.settings import INDENT_SPACES
from generate.utils import camel_to_snake_case, to_function_name, remove_non_alnum
from nlp.generate.variable import Variable


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

    def get_template_context(self, indent):
        return {}

    @classmethod
    def get_indent_string(cls, indent):
        return ' ' * indent

    def to_template(self, indent=0):
        return self.get_indent_string(indent) + self.get_template().format(**self.get_template_context(indent))

    def __str__(self):
        return self.to_template()


class Argument(TemplateMixin):
    """
    Class that represents the values that are passed to a function during runtime.

    foo(a, "b", 1)
    => a, "b" and 1 are arguments.
    """
    template = '{value}'

    def __init__(self, value):
        self.value = value

    @classmethod
    def get_string_for_template(cls, string):
        return '\'{}\''.format(string) if isinstance(string, str) else str(string)

    def get_template_context(self, indent):
        if isinstance(self.value, Variable):
            value = str(self.value)
        elif isinstance(self.value, (list, tuple, set)) and len(str(self.value)) > 100:
            if isinstance(self.value, list):
                start_symbol = '['
                end_symbol = ']'
            elif isinstance(self.value, tuple):
                start_symbol = '('
                end_symbol = ')'
            else:
                start_symbol = '{'
                end_symbol = '}'

            children = [Argument(value) for value in self.value]
            child_template = ',\n'.join(argument.to_template(indent + INDENT_SPACES) for argument in children)

            value = '{start_symbol}\n{child}\n{base_indent}{end_symbol}'.format(
                start_symbol=start_symbol,
                end_symbol=end_symbol,
                base_indent=self.get_indent_string(indent),
                child=child_template,
            )
        else:
            value = self.get_string_for_template(self.value)

        return {'value': value}


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


class PyTestMarkDecorator(Decorator):
    """A Pytest mark decorator (pytest.mark.XXX)."""
    def __init__(self, name, arguments=None):
        super().__init__('pytest.mark.{}'.format(name), arguments)

    def on_add_to_test_case(self, test_case):
        test_case.test_suite.add_import(Import('pytest'))


class PyTestParametrizeDecorator(PyTestMarkDecorator):
    def __init__(self, argument_names, argument_values):
        self.argument_names_raw = argument_names
        self.argument_names = Argument(', '.join(argument_names))
        self.argument_values = Argument(argument_values)

        super().__init__('parametrize', [self.argument_names, self.argument_values])

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
            test_case.add_parameter(Parameter(argument_name))


class DjangoDBDecorator(PyTestMarkDecorator):
    def __init__(self):
        super().__init__('django_db')


class Import(TemplateMixin):
    def __init__(self, path: str, variables=None):
        self.path = path
        self.variables = variables or []

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return self.path == other.path and self.variables == other.variables

    def get_template(self):
        if not self.variables:
            return 'import {path}'

        return 'from {path} import {variables}'

    def get_template_context(self, indent):
        return {
            'path': self.path,
            'variables': ', '.join(self.variables),
        }


class Kwarg(TemplateMixin):
    template = '{name}={value}'

    def __init__(self, name, value):
        self.name = name
        self.value = Argument(value)

    def get_template_context(self, indent):
        return {'name': self.name, 'value': self.value}


class Expression(TemplateMixin, OnAddToTestCaseListenerMixin):
    pass


class FunctionCallExpression(Expression):
    template = '{fn_name}({kwargs})'

    def __init__(self, function_name, function_kwargs):
        self.function_name = function_name
        self.function_kwargs = function_kwargs

    def get_template_context(self, indent):
        return {
            'fn_name': self.function_name,
            'kwargs': ', '.join([kwarg.to_template(indent) for kwarg in self.function_kwargs]),
        }


class ModelFactoryExpression(FunctionCallExpression):
    def __init__(self, model_interface, factory_kwargs):
        self.model_interface = model_interface
        super().__init__(self.factory_name, factory_kwargs)

    @property
    def factory_name(self):
        return '{}_factory'.format(self.get_model_in_snake_case())

    def get_model_in_snake_case(self):
        return camel_to_snake_case(self.model_interface.name)

    def on_add_to_test_case(self, test_case):
        parameter = Parameter(self.factory_name)
        test_case.add_parameter(parameter)

        # when a factory is used, there needs to be a mark for DjangoDB
        test_case.add_decorator(DjangoDBDecorator())


class ModelM2MAddExpression(Expression):
    template = '{model_instance}.{field}.add({variable})'

    def __init__(self, model, field, variable):
        self.model = model
        self.field = field
        self.variable = variable

    def get_template_context(self, indent):
        return {
            'model_instance': self.model,
            'field': self.field,
            'variable': self.variable,
        }


class Statement(TemplateMixin):
    template = '{expression}'

    def __init__(self, expression):
        self.expression = expression
        self.test_case = None

    def get_template_context(self, indent):
        return {'expression': self.expression}

    def add_to_test_case(self, test_case):
        self.test_case = test_case

        if self.expression is not None:
            self.expression.on_add_to_test_case(test_case)

    def string_matches_variable(self, string):
        return False


class AssignmentStatement(Statement):
    template = '{variable} = {expression}'

    def __init__(self, expression, variable):
        super().__init__(expression)
        self.variable = variable
        variable.set_value(self.expression)

    def string_matches_variable(self, string):
        if not self.variable:
            return False

        return self.variable.string_matches_variable(string)

    def generate_variable(self, test_case):
        if not self.variable.name_predetermined:
            similar_statements = []

            for statement in test_case.statements:
                if not isinstance(statement, AssignmentStatement):
                    continue

                if self.variable.has_similar_reference_string(statement.variable):
                    similar_statements.append(statement)

            self.variable.name_predetermined = str(len(similar_statements) + 1)

    def get_template(self):
        if self.variable:
            return self.template
        return '{expression}'

    def get_template_context(self, indent):
        context = super().get_template_context(indent)
        context['variable'] = self.variable

        return context


class PassStatement(Statement):
    template = 'pass'

    def __init__(self):
        # there is no expression in a pass statement
        super().__init__(None)


class AssertStatement(Statement):
    template = 'assert {expression}'


class RequestStatement(Statement):
    pass


class TestCase(TemplateMixin):
    template = '{decorators}{decorator_separator}def test_{name}({arguments}):\n{statements}'

    def __init__(self, name, test_suite):
        self._name = name
        self.parameters = []
        self.decorators = []
        self._statements = []
        self.test_suite = test_suite

    @property
    def name(self):
        """
        If there was a name passed, use it as a function name. If not, use the index instead.
        """
        if self._name is not None:
            return self._name

        index_in_test_suite = self.test_suite.test_cases.index(self)
        return str(index_in_test_suite)

    @property
    def statements(self):
        """
        Returns all statements of the test case. If there are none, a pass statement is given instead to make
        the test valid.
        """
        if len(self._statements) == 0:
            return [PassStatement()]
        return self._statements

    def get_template_context(self, indent):
        return {
            'decorators': '\n'.join(decorator.to_template(indent) for decorator in self.decorators),
            'decorator_separator': '\n' if len(self.decorators) > 0 else '',
            'name': to_function_name(self.name),
            'arguments': ', '.join(argument.to_template(indent) for argument in self.parameters),
            'statements': '\n'.join(statement.to_template(indent + INDENT_SPACES) for statement in self.statements),
        }

    def get_variable_by_string(self, string):
        for statement in self.statements:
            variable = getattr(statement, 'variable', None)

            if statement.string_matches_variable(string):
                return variable

        return None

    def variable_defined(self, name):
        variable_statement = self.get_variable_by_string(name)
        if variable_statement is not None:
            return variable_statement

        for parameter in self.parameters:
            if name == parameter.name:
                return True

        return False

    def add_decorator(self, decorator):
        """Add a decorator to a test case."""
        # only add a decorator if it is not already present
        if not isinstance(decorator, Decorator):
            raise ValueError('You can only add Decorator instances.')

        if decorator not in self.decorators:
            self.decorators.append(decorator)
            decorator.on_add_to_test_case(self)

    def add_statement(self, statement):
        if not isinstance(statement, Statement):
            raise ValueError('You can only add Statement instances.')

        self._statements.append(statement)
        statement.add_to_test_case(self)

    def add_parameter(self, parameter):
        if not isinstance(parameter, Parameter):
            raise ValueError('You can only add Parameter instances.')

        if parameter not in self.parameters:
            self.parameters.append(parameter)


class TestSuite(TemplateMixin):
    template = '{imports}{separator}{test_cases}\n'

    def __init__(self, name):
        self.name = name
        self.imports = []
        self.test_cases = []

    def get_template_context(self, indent):
        return {
            'imports': '\n'.join(import_entry.to_template(indent) for import_entry in self.imports),
            'separator': '\n\n\n' if len(self.imports) > 0 else '',
            'test_cases': '\n\n\n'.join(test_case.to_template(indent) for test_case in self.test_cases)
        }

    def create_and_add_test_case(self, name):
        test_case = TestCase(name, self)
        self.test_cases.append(test_case)
        return test_case

    def add_import(self, import_instance):
        """Add an import to the test suite/ the test file."""
        if import_instance not in self.imports:
            self.imports.append(import_instance)
