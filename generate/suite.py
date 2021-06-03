from typing import Iterable

from generate.utils import camel_to_snake_case


class TemplateMixin(object):
    template = None

    def get_template(self):
        return self.template

    def get_template_context(self, intend):
        return {}

    def to_template(self, intend=0):
        return ' ' * intend + self.get_template().format(**self.get_template_context(intend))

    def __str__(self):
        return self.to_template()


class Import(TemplateMixin):
    path = None
    variables = []
    template = 'from {path} import {variables}'

    def __init__(self, path: str, variables: Iterable[str]):
        self.path = path
        self.variables = variables

    def get_template_context(self, intend):
        return {
            'path': self.path,
            'variables': ', '.join(self.variables),
        }


class TestCaseArgument(TemplateMixin):
    template = '{name}'

    def __init__(self, name):
        self.name = name

    def get_template_context(self, intend):
        return {'name': self.name}


class Kwarg(object):
    def __init__(self, name, value):
        self.name = name
        self.value = value


class Variable(TemplateMixin):
    name = None
    template = '{name}'

    def __init__(self, name):
        self.name = name

    def get_template_context(self, intend):
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

    def get_template_context(self, intend):
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

    def get_template_context(self, intend):
        return {
            'variable': self.variable,
            'expression': self.expression,
        }


class PassStatement(Statement):
    template = 'pass'

    def __init__(self):
        super().__init__(None)


class AssertStatement(Statement):
    template = 'assert {expression}'


class RequestStatement(Statement):
    pass


class TestCase(TemplateMixin):
    arguments = []
    decorators = []
    test_suite = None

    def __init__(self, name, test_suite):
        self._name = name
        self.arguments = []
        self.decorators = []
        self._statements = []
        self.test_suite = test_suite

    @property
    def name(self):
        if self._name is not None:
            return self._name

        index_in_test_suite = self.test_suite.test_cases.index(self)
        return str(index_in_test_suite)

    @property
    def statements(self):
        if len(self._statements) == 0:
            return [PassStatement()]
        return self._statements

    def get_template(self):
        return 'def test_{name}({arguments}):\n{statements}'

    def get_template_context(self, intend):
        # remove special characters and multiple spaces from name
        no_special_char_name = ''.join(e if e.isalnum() else ' ' for e in self.name.lower())
        clean_name = '_'.join(no_special_char_name.split())

        return {
            'name': clean_name,
            'arguments': ', '.join(str(argument) for argument in self.arguments),
            'statements': '\n'.join(statement.to_template(intend + 4) for statement in self.statements),
        }

    def get_value_for_variable(self, name):
        for statement in self.statements:
            if not hasattr(statement, 'variable'):
                continue

            if statement.variable and name == statement.variable.name:
                return statement.expression
        return None

    def add_statement(self, statement):
        self._statements.append(statement)
        statement.add_to_test_case(self)


class TestSuite(TemplateMixin):
    imports = []
    test_cases = []

    def __init__(self, name):
        self.name = name
        self.imports = []
        self.test_cases = []

    def get_template(self):
        return '{imports}{separator}{test_cases}\n'

    def get_template_context(self, intend):
        return {
            'imports': '\n'.join(import_entry.to_template(intend) for import_entry in self.imports),
            'separator': '\n\n' if len(self.imports) > 0 else '',
            'test_cases': '\n\n'.join(test_case.to_template(intend) for test_case in self.test_cases)
        }

    def add_test_case(self, name):
        test_case = TestCase(name, self)
        self.test_cases.append(test_case)
        return test_case
