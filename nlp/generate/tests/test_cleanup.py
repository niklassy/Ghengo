from nlp.generate.argument import Argument
from nlp.generate.attribute import Attribute
from nlp.generate.expression import FunctionCallExpression
from nlp.generate.pytest.suite import PyTestTestSuite
from nlp.generate.statement import AssignmentStatement
from nlp.generate.variable import Variable
from nlp.tests.utils import MockTranslator


def test_cleanup_variables(mocker):
    """Check if variables are cleaned up."""
    mocker.patch('deep_translator.GoogleTranslator.translate', MockTranslator())
    suite = PyTestTestSuite('yup')
    test_case = suite.create_and_add_test_case('foo')

    var_1 = Variable('1', 'foo')
    var_2 = Variable('2', 'foo')
    var_3 = Variable('foo', 'bar')
    var_4 = Variable('baz', 'foo')

    test_case.add_statement(
        AssignmentStatement(variable=var_1, expression=Argument('')),
    )
    test_case.add_statement(
        AssignmentStatement(
            variable=var_2,
            expression=FunctionCallExpression(Attribute(var_1.get_reference(), 'foo'), [])),
    )
    test_case.add_statement(
        AssignmentStatement(
            variable=var_3,
            expression=FunctionCallExpression(Attribute(var_1.get_reference(), 'foo'), [])
        ),
    )
    test_case.add_statement(
        AssignmentStatement(
            variable=var_4,
            expression=FunctionCallExpression(Attribute(var_1.get_reference(), 'foo'), [var_2.get_reference()]),
        ),
    )

    # clean it all up
    suite.clean_up()

    # check that only the variables exist that are needed
    assert len(test_case.statements) == 4
    assert bool(test_case.statements[0].variable)
    assert bool(test_case.statements[1].variable)
    assert not bool(test_case.statements[2].variable)   # <- the variables of the last two statements are not used
    assert not bool(test_case.statements[3].variable)   # afterwards

    # check if the var_4 exists if we use it in a statement afterwards
    test_case.statements[3].variable = var_4
    test_case.add_statement(
        AssignmentStatement(variable=var_3, expression=Attribute(var_4.get_reference(), 'bar')),
    )
    suite.clean_up()
    assert bool(test_case.statements[3].variable)
