from nlp.generate.decorator import Decorator
from nlp.generate.mixin import TemplateMixin
from nlp.generate.parameter import Parameter
from nlp.generate.replaceable import Replaceable
from settings import PYTHON_INDENT_SPACES
from nlp.generate.statement import PassStatement, Statement, AssignmentStatement
from nlp.generate.utils import to_function_name
from nlp.generate.warning import GenerationWarningCollection


class Import(Replaceable, TemplateMixin):
    def __init__(self, path: str, variables=None):
        super().__init__()
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

    def get_template_context(self, line_indent, indent):
        return {
            'path': self.path,
            'variables': ', '.join(self.variables),
        }


class ImportPlaceholder(Import):
    """
    This import can be used as a placeholder if a given import is not valid/ does not really exist and
    would generate an error in the code.
    """
    todo_message = '# TODO: the import for the following values either was not found or does not exist. If the ' \
                   'import does\n exist in your code, you have to set the value manually. If it does exist, try ' \
                   'creating the\n import in your code first.'

    def __init__(self, variables):
        super().__init__('', variables)

    def get_template(self):
        return '{todo_message}\n{variables}'

    def get_template_context(self, line_indent, indent):
        todo_message = '\n#    '.join(self.todo_message.split('\n'))
        variables = '\n'.join('{} = None   # <- fix'.format(v) for v in self.variables)

        return {'variables': variables, 'todo_message': todo_message}


class TestCaseBase(Replaceable, TemplateMixin):
    class ParameterAlreadyPresent(Exception):
        pass

    class DecoratorAlreadyPresent(Exception):
        pass

    def __init__(self, name, test_suite):
        super().__init__()
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

    def get_all_statements_with_expression(self, expression_cls):
        """
        Returns all statements that have a certain expression class.
        """
        return [s for s in self.statements if isinstance(s.expression, expression_cls)]

    @property
    def statements(self):
        """
        Returns all statements of the test case. If there are none, a pass statement is given instead to make
        the test valid.
        """
        if len(self._statements) == 0:
            return [PassStatement()]
        return self._statements

    def get_template_context(self, line_indent, indent):
        return {
            'decorators': '\n'.join(decorator.to_template(line_indent) for decorator in self.decorators),
            'decorator_separator': '\n' if len(self.decorators) > 0 else '',
            'name': to_function_name('test_{}'.format(self.name.replace(' ', '_'))),
            'parameters': ', '.join(para.to_template() for para in self.parameters),
            'statements': '\n'.join(statement.to_template(
                line_indent + PYTHON_INDENT_SPACES, line_indent + PYTHON_INDENT_SPACES) for statement in self.statements),
        }

    def get_variable_by_string(self, string, reference_string):
        """Returns a variable with a given string."""
        for statement in self.statements:
            variable = getattr(statement, 'variable', None)

            if statement.string_matches_variable(string, reference_string):
                return variable

        return None

    def variable_defined(self, name, reference_string):
        """Check if the given variable is defined."""
        variable_statement = self.get_variable_by_string(name, reference_string)
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

    def clean_up(self):
        """
        Cleanup up all the statements in a test case.
        """
        statement_copy = self.statements.copy()
        referenced_variables = []

        # for each statement: clean it up and save the variables that it uses
        for statement in reversed(statement_copy):
            statement.clean_up(self, referenced_variables)
            referenced_variables += statement.get_referenced_variables()


class TestSuiteBase(Replaceable, TemplateMixin):
    test_case_class = None

    def __init__(self, name):
        super().__init__()
        self.name = name
        self.warning_collection = GenerationWarningCollection()
        self.imports = []
        self.test_cases = []

    def clean_up(self):
        """
        Can be called after everything is ready. This will do everything as a last step to cleanup before exporting.
        """
        for test_case in self.test_cases:
            test_case.clean_up()

    def get_template_context(self, line_indent, indent):
        return {
            'warning_collection': self.warning_collection.to_template(),
            'imports': '\n'.join(import_entry.to_template(line_indent) for import_entry in self.imports),
            'separator': '\n\n\n' if len(self.imports) > 0 else '',
            'test_cases': '\n\n\n'.join(test_case.to_template(line_indent) for test_case in self.test_cases)
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
