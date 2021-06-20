from nlp.generate.argument import Kwarg
from nlp.generate.expression import Expression, FunctionCallExpression, ModelFactoryExpression, ModelM2MAddExpression
from nlp.generate.statement import Statement


def test_expression_as_statement():
    """Check that expressions can be converted to a simple statement."""
    exp = Expression()
    statement = exp.as_statement()
    assert statement.__class__ == Statement
    assert statement.expression == exp


def test_function_call_expression():
    """Check that FunctionCallExpression returns the correct template."""
    exp = FunctionCallExpression('foo', [Kwarg('bar', 123)])
    assert exp.to_template() == 'foo(bar=123)'
    assert exp.to_template(4, 4) == '    foo(bar=123)'


def test_model_factory_expression():
    """Check that the model factory expression handled the interface and the data correctly."""
    class ModelInterface:
        name = 'order'

    exp = ModelFactoryExpression(ModelInterface(), [Kwarg('bar', 123)])
    assert exp.factory_name == 'order_factory'
    assert exp.to_template() == 'order_factory(bar=123)'
    assert exp.to_template(4, 4) == '    order_factory(bar=123)'


def test_m2m_add_expression():
    """Check that m2m add expression creates the correct template."""
    exp = ModelM2MAddExpression(model_instance_variable='foo', field='baz', add_variable='bar')
    assert exp.to_template() == 'foo.baz.add(bar)'
