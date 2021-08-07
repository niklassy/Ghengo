from nlp.generate.argument import Argument
from nlp.generate.decorator import Decorator


def test_decorator_no_arguments():
    """Check that the template without arguments is rendered correctly."""
    assert Decorator('foo').to_template() == '@foo'
    assert Decorator(123).to_template() == '@123'


def test_decorator_with_arguments():
    """Check that the template with arguments is rendered correctly."""
    arguments = [Argument('value_1'), Argument(123)]
    assert Decorator('foo', arguments).to_template() == '@foo(\'value_1\', 123)'
    assert Decorator(123, arguments).to_template() == '@123(\'value_1\', 123)'


def test_decorator_equals():
    """Check that _comparison is handled correctly for decorators."""
    dec = Decorator('foo', [Argument('value_1'), Argument(123)])
    assert dec != '123'
    assert dec is not None
    assert dec != Decorator('123')
    assert dec != Decorator('123', [Argument('value_1'), Argument(123)])
    assert dec == Decorator('foo', [Argument('value_1'), Argument(123)])
    assert dec == Decorator('foo', [Argument(123)])
    assert dec == Decorator('foo')
