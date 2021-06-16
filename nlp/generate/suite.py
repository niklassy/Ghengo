from nlp.generate.decorator import Decorator
from nlp.generate.mixin import TemplateMixin
from nlp.generate.parameter import Parameter
from nlp.generate.settings import INDENT_SPACES
from nlp.generate.statement import PassStatement, Statement
from nlp.generate.utils import to_function_name


class Import(TemplateMixin):
    def __init__(self, path: str, variables=None):
        self.path = path
        if variables is None:
            variables = []

        if not isinstance(variables, list):
            variables = [variables]

        self.variables = variables

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return self.path == other.path

    def get_template(self):
        if not self.variables:
            return 'import {path}'

        return 'from {path} import {variables}'

    def get_template_context(self, indent):
        return {
            'path': self.path,
            'variables': ', '.join(self.variables),
        }


class TestCaseBase(TemplateMixin):
    type = None

    class ParameterAlreadyPresent(Exception):
        pass

    class DecoratorAlreadyPresent(Exception):
        pass

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

        try:
            index_in_test_suite = self.test_suite.test_cases.index(self)
        except ValueError:
            index_in_test_suite = 0

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
            'parameters': ', '.join(para.to_template() for para in self.parameters),
            'statements': '\n'.join(statement.to_template(indent + INDENT_SPACES) for statement in self.statements),
        }

    def get_variable_by_string(self, string):
        """Returns a variable with a given string."""
        for statement in self.statements:
            variable = getattr(statement, 'variable', None)

            if statement.string_matches_variable(string):
                return variable

        return None

    def variable_defined(self, name):
        """Check if the given variable is defined."""
        variable_statement = self.get_variable_by_string(name)
        if variable_statement is not None:
            return True

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
        else:
            raise self.DecoratorAlreadyPresent()

    def add_statement(self, statement):
        if not isinstance(statement, Statement):
            raise ValueError('You can only add Statement instances.')

        self._statements.append(statement)
        statement.on_add_to_test_case(self)

    def add_parameter(self, parameter):
        if not isinstance(parameter, Parameter):
            raise ValueError('You can only add Parameter instances.')

        if parameter not in self.parameters:
            self.parameters.append(parameter)
        else:
            raise self.ParameterAlreadyPresent()


class TestSuiteBase(TemplateMixin):
    test_case_class = None
    type = None

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

    def create_and_add_test_case(self, name) -> TestCaseBase:
        """Creates a test case and adds it to the suite."""
        test_case = self.test_case_class(name, self)
        self.test_cases.append(test_case)
        return test_case

    def add_import(self, import_instance):
        """Add an import to the test suite/ the test file."""
        if import_instance not in self.imports:
            self.imports.append(import_instance)
        else:
            for existing_import in self.imports:
                if existing_import == import_instance:
                    # search for the existing import and add the variables to that import if not already present
                    for variable in import_instance.variables:
                        if variable not in existing_import.variables:
                            existing_import.variables.append(variable)
