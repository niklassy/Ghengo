from nlp.generate.argument import Argument, Kwarg


def test_argument_string():
    """Check that strings are correctly transformed."""
    arg = Argument('123')
    assert arg.get_string_for_template('456') == '\'456\''
    assert arg.get_string_for_template(456) == '456'
    assert arg.get_string_for_template([456]) == '[456]'


def test_argument_long_value():
    """Check the Argument handled long values correctly."""
    value_list = [
        '1234567890123456789012345678901234567890',
        '12345678901234567890',
        '1234567890123456789012345678901234567890',
    ]
    arg = Argument(value_list)
    value = arg.get_template_context(0).get('value')
    desired_output = "[\n    '1234567890123456789012345678901234567890',\n    '12345678901234567890',\n    " \
                     "'1234567890123456789012345678901234567890'\n]"
    assert value == desired_output


def test_kwarg_template():
    """Check that Kwarg creates a correct template."""
    assert Kwarg('foo', ['123']).to_template() == 'foo=[\'123\']'
    assert Kwarg('foo', [123]).to_template() == 'foo=[123]'
    assert Kwarg('foo', 123).to_template() == 'foo=123'
    assert Kwarg('foo', '123').to_template() == 'foo=\'123\''
