from typing import Iterable

from generate.utils import camel_to_snake_case


class TemplateMixin(object):
    template = None

    def get_template(self):
        return self.template

    def get_template_context(self):
        return {}

    def to_template(self):
        return self.template.format(**self.get_template_context())

    def __str__(self):
        return self.to_template()


class Import(TemplateMixin):
    path = None
    variables = []
    template = 'from {path} import {variables}'

    def __init__(self, path: str, variables: Iterable[str]):
        self.path = path
        self.variables = variables

    def get_template_context(self):
        return {
            'path': self.path,
            'variables': ', '.join(self.variables),
        }


class TestCaseArgument(object):
    def __init__(self, name):
        self.name = name


class Kwarg(object):
    def __init__(self, name, value):
        self.name = name
        self.value = value


class Variable(TemplateMixin):
    name = None
    template = '{name}'

    def __init__(self, name):
        self.name = name

    def get_template_context(self):
        return {'name': self.name}


class Expresion(TemplateMixin):
    @property
    def return_value(self):
        return None

    def on_add_to_test_case(self, test_case):
        pass


class ModelFactoryExpression(Expresion):
    template = '{factory_name}({kwargs})'

    def __init__(self, model_interface, factory_kwargs):
        self.model_interface = model_interface
        self.factory_kwargs = factory_kwargs

    @property
    def factory_name(self):
        model_in_snake_case = camel_to_snake_case(self.model_interface.name)
        return '{}_factory'.format(model_in_snake_case)

    def get_template_context(self):
        return {
            'factory_name': self.factory_name,
            'kwargs': ', '.join(['{}={}'.format(kwarg.name, kwarg.value) for kwarg in self.factory_kwargs])
        }

    def on_add_to_test_case(self, test_case):
        argument = TestCaseArgument(self.factory_name)
        test_case.arguments.append(argument)


class Statement(TemplateMixin):
    expression = None

    def __init__(self, expression):
        self.expression = expression
        self.test_case = None

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

    def get_template_context(self):
        return {
            'variable': self.variable,
            'expression': self.expression,
        }


class AssertStatement(Statement):
    template = 'assert {expression}'


class RequestStatement(Statement):
    pass


class TestCase(object):
    arguments = []
    decorators = []
    statements = []
    test_suite = None

    def __init__(self, test_suite):
        self.arguments = []
        self.decorators = []
        self.statements = []
        self.test_suite = test_suite

    def get_value_for_variable(self, name):
        for statement in self.statements:
            if statement.variable and name == statement.variable.name:
                return statement.expression
        return None

    def add_statement(self, statement):
        self.statements.append(statement)


class TestSuite(object):
    imports = []
    test_cases = []

    def __init__(self, name):
        self.name = name

    def add_test_case(self):
        test_case = TestCase(self)
        self.test_cases.append(test_case)
        return test_case
