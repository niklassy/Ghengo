from nlp.generate.argument import Kwarg
from nlp.generate.decorator import Decorator
from nlp.generate.expression import FunctionCallExpression
from nlp.generate.parameter import Parameter
from nlp.generate.statement import PassStatement, AssertStatement, AssignmentStatement
from nlp.generate.suite import Import, TestCaseBase, TestSuiteBase
from nlp.generate.variable import Variable


def test_import_template():
    """Check that import handles its template correctly."""
    assert Import('nlp.generate.suite', ['Import', 'TestCase']).to_template() == \
           'from nlp.generate.suite import Import, TestCase'
    assert Import('nlp.generate.suite', 'Import').to_template() == 'from nlp.generate.suite import Import'
    assert Import('pytest').to_template() == 'import pytest'


def test_import_equals():
    """Check that the paths are compared for imports"""
    assert Import('pytest') == Import('pytest', ['foo', 'bar'])
    assert Import('pytest') != Import('qweqwe', ['foo', 'bar'])


class TestingTestSuiteBase(TestSuiteBase):
    test_case_class = TestCaseBase


def test_test_case_base_name():
    """Check that the name of test case is correctly generated."""
    assert TestCaseBase('foo', TestingTestSuiteBase('bar')).name == 'foo'
    assert TestCaseBase(None, TestingTestSuiteBase('bar')).name == '0'
    suite = TestingTestSuiteBase('bar')
    assert suite.create_and_add_test_case(None).name == '0'
    assert suite.create_and_add_test_case('booz').name == 'booz'
    assert suite.create_and_add_test_case(None).name == '2'


def test_test_case_statements():
    """Check that the test case base inserts a pass statement on default if no other exist."""
    test_case = TestingTestSuiteBase('bar').create_and_add_test_case('foo')
    assert len(test_case.statements) == 1
    assert isinstance(test_case.statements[0], PassStatement)
    statement = AssertStatement(FunctionCallExpression('foo', [Kwarg('bar', 123)]))
    test_case.add_statement(statement)
    assert len(test_case.statements) == 1
    assert test_case.statements[0] == statement


def test_test_case_get_variable_by_string():
    """Check that you can extract variables from a test case."""
    test_case = TestingTestSuiteBase('bar').create_and_add_test_case('foo')
    var = Variable('other_name', 'my_reference')
    statement = AssignmentStatement(FunctionCallExpression('foo', [Kwarg('bar', 123)]), var)
    assert test_case.get_variable_by_string('other_name', 'my_reference') is None
    test_case.add_statement(statement)
    assert test_case.get_variable_by_string('other_name', 'my_reference') == var


def test_test_case_variable_defined():
    """Check that you can check if a variable is defined in either the parameters or in any statement."""
    test_case = TestingTestSuiteBase('bar').create_and_add_test_case('foo')
    param = Parameter('param')
    test_case.add_parameter(param)
    assert test_case.variable_defined('param', None) is True
    assert test_case.variable_defined('param_123', None) is False
    assert test_case.variable_defined('other_name', None) is False
    var = Variable('other_name', 'my_reference')
    statement = AssignmentStatement(FunctionCallExpression('foo', [Kwarg('bar', 123)]), var)
    test_case.add_statement(statement)
    assert test_case.variable_defined('other_name', 'my_reference') is True


def test_test_case_add_param():
    """Check that adding parameters is only okay once."""
    test_case = TestingTestSuiteBase('bar').create_and_add_test_case('foo')
    param = Parameter('param')
    test_case.add_parameter(param)
    try:
        test_case.add_parameter(param)
        assert False
    except TestCaseBase.ParameterAlreadyPresent:
        pass


def test_test_case_add_decorator():
    """Check that adding a decorator is only okay once."""
    test_case = TestingTestSuiteBase('bar').create_and_add_test_case('foo')
    dec = Decorator('foo')
    test_case.add_decorator(dec)
    assert dec in test_case.decorators
    try:
        test_case.add_decorator(dec)
        assert False
    except TestCaseBase.DecoratorAlreadyPresent:
        pass


def test_test_case_template_context_empty():
    """Check that an empty test case returns the correct context for the template."""
    test_case = TestingTestSuiteBase('bar').create_and_add_test_case('foo')
    context = test_case.get_template_context(0)
    assert context['decorator_separator'] == ''
    assert context['decorators'] == ''
    assert context['name'] == 'test_foo'
    assert context['parameters'] == ''
    assert context['statements'] == '    pass'


def test_test_case_template_context_with_data():
    """Check that a test case with data returns the correct context for the template."""
    test_case = TestingTestSuiteBase('bar').create_and_add_test_case('foo')

    test_case.add_decorator(Decorator('foo'))
    test_case.add_decorator(Decorator('foo2'))

    test_case.add_parameter(Parameter('param'))
    test_case.add_parameter(Parameter('param_2'))

    test_case.add_statement(AssertStatement(FunctionCallExpression('foo', [Kwarg('bar', 123)])))

    context = test_case.get_template_context(0)
    assert context['decorator_separator'] == '\n'
    assert context['decorators'] == '@foo\n@foo2'
    assert context['name'] == 'test_foo'
    assert context['parameters'] == 'param, param_2'
    assert context['statements'] == '    assert foo(bar=123)'


def test_test_suite_create_and_add_test():
    """Check that test suites are able to create test cases inside of them."""
    suite = TestingTestSuiteBase('foo')
    assert suite.test_cases == []
    test_case = suite.create_and_add_test_case('bar')
    assert len(suite.test_cases) == 1
    assert suite.test_cases[0] == test_case


def test_test_suite_add_import():
    """Check that imports in test suites are handles correctly."""
    suite = TestingTestSuiteBase('foo')
    assert suite.imports == []
    import_1 = Import('nlp.generate.statement', ['PassStatement', 'AssertStatement'])
    suite.add_import(import_1)
    assert len(suite.imports) == 1
    assert suite.imports[0] == import_1
    import_2 = Import('nlp.generate.statement', ['PassStatement', 'AssertStatement', 'AssignmentStatement'])
    suite.add_import(import_2)
    assert len(suite.imports) == 1
    assert suite.imports[0] == import_1
    assert len(import_1.variables) == 3
    import_3 = Import('pytest')
    suite.add_import(import_3)
    assert len(suite.imports) == 2


def test_test_suite_template_context():
    """Check that the context of the test suite is returned correctly."""
    suite = TestingTestSuiteBase('foo')
    suite.add_import(Import('nlp.generate.statement', ['PassStatement', 'AssertStatement']))
    suite.add_import(Import('pytest'))
    suite.create_and_add_test_case('bar')

    context = suite.get_template_context(0)
    assert context['separator'] == '\n\n\n'
    assert context['imports'] == 'from nlp.generate.statement import PassStatement, AssertStatement\nimport pytest'
    assert context['test_cases'] == ''
