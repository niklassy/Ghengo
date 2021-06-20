from nlp.generate.parameter import Parameter


def test_parameter_template():
    """Check that the template for parameters is handled as wanted."""
    param = Parameter('foo')
    assert param.to_template() == 'foo'
    param.indent = 5
    assert param.to_template() == '     foo'


def test_parameter_equals():
    """Check that the comparison of parameter is handled correctly."""
    param = Parameter('foo')
    assert param != 'foo'
    assert param != 'qweqwe'
    assert param != 123
    assert param != Parameter('foo123')
    assert param == Parameter('foo')
