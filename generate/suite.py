from generate.utils import camel_to_snake_case, to_function_name


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

    def to_template(self, indent=0):
        return ' ' * indent + self.get_template().format(**self.get_template_context(indent))

    def __str__(self):
        return self.to_template()


class Decorator(TemplateMixin, OnAddToTestCaseListenerMixin):
    template = '@{decorator_name}'

    def __init__(self, name):
        self.name = name

    def get_template_context(self, indent):
        return {'decorator_name': self.name}

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return self.name == other.name


class PyTestMarkDecorator(Decorator):
    """A Pytest mark decorator (pytest.mark.XXX)."""
    def __init__(self, name):
        super().__init__('pytest.mark.{}'.format(name))

    def on_add_to_test_case(self, test_case):
        test_case.test_suite.add_import(Import('pytest'))


class DjangoDBDecorator(PyTestMarkDecorator):
    def __init__(self):
        super().__init__('django_db')


class Import(TemplateMixin):
    path = None
    variables = []

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


class TestCaseArgument(TemplateMixin):
    template = '{name}'

    def __init__(self, name):
        self.name = name

    def get_template_context(self, indent):
        return {'name': self.name}


class Kwarg(TemplateMixin):
    template = '{name}={value}'

    def __init__(self, name, value):
        self.name = name
        self.value = value

    def get_template_context(self, indent):
        return {'name': self.name, 'value': self.value}


class Variable(TemplateMixin):
    name = None
    template = '{name}'

    def __init__(self, name):
        self.name = name

    def get_template_context(self, indent):
        return {'name': self.name}


class Expresion(TemplateMixin, OnAddToTestCaseListenerMixin):
    pass


class FunctionCallExpression(Expresion):
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
        model_in_snake_case = camel_to_snake_case(self.model_interface.name)
        return '{}_factory'.format(model_in_snake_case)

    def on_add_to_test_case(self, test_case):
        argument = TestCaseArgument(self.factory_name)
        test_case.arguments.append(argument)
        test_case.add_decorator(DjangoDBDecorator())


class Statement(TemplateMixin):
    def __init__(self, expression):
        self.expression = expression
        self.test_case = None

    def get_template_context(self, indent):
        return {'expression': self.expression}

    def add_to_test_case(self, test_case):
        self.test_case = test_case

        if self.expression is not None:
            self.expression.on_add_to_test_case(test_case)


class AssignmentStatement(Statement):
    variable = None
    template = '{variable} = {expression}'

    def __init__(self, expression, variable):
        super().__init__(expression)
        self.variable = variable

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
        self.arguments = []
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
            'arguments': ', '.join(argument.to_template(indent) for argument in self.arguments),
            'statements': '\n'.join(statement.to_template(indent + 4) for statement in self.statements),
        }

    def get_value_for_variable(self, name):
        """Returns the value for a given variable in the test case."""
        for statement in self.statements:
            variable = getattr(statement, 'variable', None)

            if variable and name == variable.name:
                return statement.expression
        return None

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
