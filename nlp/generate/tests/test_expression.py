from django.contrib.auth.models import User

from django_meta.model import ModelWrapper, AbstractModelWrapper
from nlp.generate.argument import Kwarg
from nlp.generate.expression import Expression, FunctionCallExpression, ModelFactoryExpression, ModelM2MAddExpression, \
    ModelQuerysetBaseExpression
from nlp.generate.pytest.suite import PyTestTestSuite
from nlp.generate.statement import Statement
from nlp.generate.suite import Import, ImportPlaceholder
from nlp.generate.variable import Variable


def test_expression_as_statement():
    """Check that expressions can be converted to a simple statement."""
    exp = Expression('')
    statement = exp.as_statement()
    assert statement.__class__ == Statement
    assert statement.expression == exp


def test_function_call_expression():
    """Check that FunctionCallExpression returns the correct template."""
    exp = FunctionCallExpression('foo', [Kwarg('bar', 123)])
    assert exp.to_template() == 'foo(bar=123)'
    assert exp.to_template(4, 4) == '    foo(bar=123)'


def test_model_factory_expression():
    """Check that the model factory expression handled the wrapper and the data correctly."""
    class CustomModelWrapper:
        name = 'order'

    exp = ModelFactoryExpression(CustomModelWrapper(), [Kwarg('bar', 123)])
    assert exp.factory_name == 'order_factory'
    assert exp.to_template() == 'order_factory(bar=123)'
    assert exp.to_template(4, 4) == '    order_factory(bar=123)'


def test_m2m_add_expression():
    """Check that m2m add expression creates the correct template."""
    var = Variable('foo', 'foo')
    exp = ModelM2MAddExpression(model_instance_variable_ref=var.get_reference(), field='baz', add_variable_ref='bar')
    assert exp.to_template() == 'foo.baz.add(bar)'


def test_model_queryset_base_expression():
    """Check that ModelQuerysetBaseExpression generates the correct template."""
    exp = ModelQuerysetBaseExpression(ModelWrapper(User, None), 'filter', [])
    assert exp.to_template() == 'User.objects.filter()'
    exp_2 = ModelQuerysetBaseExpression(AbstractModelWrapper('Roof'), 'all', [])
    assert exp_2.to_template() == 'Roof.objects.all()'


def test_model_queryset_base_expression_add_to_test_case():
    """Check that the ModelQuerysetBaseExpression adds the correct import to the test case."""
    suite = PyTestTestSuite('foo')
    test_case = suite.create_and_add_test_case('bar')

    exp = ModelQuerysetBaseExpression(ModelWrapper(User, None), 'filter', [])
    exp.on_add_to_test_case(test_case)
    exp_2 = ModelQuerysetBaseExpression(AbstractModelWrapper('Roof'), 'filter', [])
    exp_2.on_add_to_test_case(test_case)

    assert len(suite.imports) == 2
    assert isinstance(suite.imports[0], Import)
    assert isinstance(suite.imports[1], ImportPlaceholder)

