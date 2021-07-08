from nlp.generate.argument import Kwarg
from nlp.generate.pytest import PyTestModelFactoryExpression
from nlp.generate.pytest.suite import PyTestTestSuite


def test_pytest_model_factory_expression():
    """Check that PyTestTestSuite adds decorator and parameter to the test case."""
    class ModelAdapter:
        name = 'Order'

    suite = PyTestTestSuite('foo')
    test_case = suite.create_and_add_test_case('bar')
    expr = PyTestModelFactoryExpression(ModelAdapter(), [Kwarg('bar', 123)])
    assert len(test_case.parameters) == 0
    assert len(test_case.decorators) == 0
    expr.on_add_to_test_case(test_case)
    assert len(test_case.parameters) == 1
    assert test_case.parameters[0].name == expr.factory_name
    assert len(test_case.decorators) == 1
    assert test_case.decorators[0].name == 'pytest.mark.django_db'
    expr.on_add_to_test_case(test_case)
    assert len(test_case.parameters) == 1
    assert test_case.parameters[0].name == expr.factory_name
    assert len(test_case.decorators) == 1
    assert test_case.decorators[0].name == 'pytest.mark.django_db'
