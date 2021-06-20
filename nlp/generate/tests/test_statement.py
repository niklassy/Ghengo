from nlp.generate.argument import Kwarg
from nlp.generate.expression import FunctionCallExpression
from nlp.generate.statement import Statement, AssignmentStatement, PassStatement, AssertStatement
from nlp.generate.variable import Variable


def test_statement_template():
    """Check that the statement creates is template correctly."""
    exp = FunctionCallExpression('foo', [Kwarg('bar', 123)])
    statement = Statement(exp)
    assert statement.to_template() == exp.to_template()
    assert statement.to_template(5) == exp.to_template(5)


class CustomExpression(FunctionCallExpression):
    def on_add_to_test_case(self, test_case):
        self._on_add_to_test_case_called = True


def test_statement_add_to_test_case():
    """Check that statements can be added to test cases."""
    class MyTestCase:
        pass

    test_case = MyTestCase()
    exp = CustomExpression('foo', [Kwarg('bar', 123)])
    statement = Statement(exp)
    statement.on_add_to_test_case(test_case)
    assert statement.test_case == test_case
    assert exp._on_add_to_test_case_called is True


def test_statement_string_matches_variable():
    """Check that the default statement always returns False for a variable."""
    assert Statement(FunctionCallExpression('foo', [Kwarg('bar', 123)])).string_matches_variable('123', '') is False
    assert Statement(FunctionCallExpression('foo', [Kwarg('bar', 123)])).string_matches_variable('qwe', '') is False
    assert Statement(FunctionCallExpression('foo', [Kwarg('bar', 123)])).string_matches_variable(None, '') is False
    assert Statement(FunctionCallExpression('foo', [Kwarg('bar', 123)])).string_matches_variable(['123'], '') is False


def test_assignment_statement_string_matches_variable():
    """Check that AssignmentStatement can be used to check the variable."""
    statement_1 = AssignmentStatement(FunctionCallExpression('foo', [Kwarg('bar', 123)]), Variable('', ''))
    assert statement_1.string_matches_variable('123', '') is False
    assert statement_1.string_matches_variable(123, '') is False
    assert statement_1.string_matches_variable('werwerwer', '') is False

    statement_2 = AssignmentStatement(FunctionCallExpression('foo', [Kwarg('bar', 123)]), Variable('name', ''))
    assert statement_2.string_matches_variable('name', '') is True
    assert statement_2.string_matches_variable('123', '') is False


def test_assignment_statement_template():
    """Check that the AssignmentStatement handles templates correctly."""
    exp = FunctionCallExpression('foo', [Kwarg('bar', 123)])
    assert AssignmentStatement(exp, Variable('', '')).to_template() == 'foo(bar=123)'
    assert AssignmentStatement(exp, Variable('var_name', '')).to_template() == 'var_name = foo(bar=123)'
    statement = AssignmentStatement(exp, Variable('var_name', ''))
    statement.indent = 5
    assert statement.to_template() == '     var_name = foo(bar=123)'


def test_assignment_statement_generate_variable_no_effect():
    """Check that the generation of variables works as wanted if there is already a variable."""
    exp = FunctionCallExpression('foo', [Kwarg('bar', 123)])
    statement = AssignmentStatement(exp, Variable('name', ''))
    statement.generate_variable(None)
    assert statement.variable.name_predetermined == 'name'


def test_assignment_statement_generate_variable_with_effect():
    """Check that the generation of variables works as wanted if there is no variable."""
    exp = FunctionCallExpression('foo', [Kwarg('bar', 123)])

    class MyTest:
        statements = [
            AssignmentStatement(exp, Variable('other_name', 'my_reference')),
            Statement(exp),
            AssignmentStatement(exp, Variable('other_name', 'some_other_reference')),
        ]

    statement = AssignmentStatement(exp, Variable('', 'my_reference'))
    assert not bool(statement.variable)
    statement.generate_variable(MyTest())
    assert statement.variable.name_predetermined == '2'
    assert bool(statement.variable)


def test_pass_statement_template():
    """Check that the pass statement handles its template correctly."""
    statement = PassStatement()
    assert statement.to_template() == 'pass'
    statement.indent = 4
    assert statement.to_template() == '    pass'


def test_assert_statement_template():
    """Check that the assert statement handles its template correctly."""
    statement = AssertStatement(FunctionCallExpression('foo', [Kwarg('bar', 123)]))
    assert statement.to_template() == 'assert foo(bar=123)'
    statement.indent = 4
    assert statement.to_template() == '    assert foo(bar=123)'
