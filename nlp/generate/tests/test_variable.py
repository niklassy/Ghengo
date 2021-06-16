from nlp.generate.variable import Variable


def test_variable_copy():
    """Check that copying variables works as expected."""
    var = Variable('foo', 'reference')
    var.set_value('qweqwe')
    copy = var.copy()
    assert copy == var
    assert copy.value == 'qweqwe'
    assert copy.name == 'foo'


def test_variable_as_bool():
    """Check that the name is used to determine if the variable exists or not."""
    assert bool(Variable('', 'ref')) is False
    assert bool(Variable('name', 'ref')) is True


def test_variable_equals():
    """Check that two variables are the same if their name and value are equal."""
    var = Variable('name', 'ref')
    var.set_value('1234567')
    assert var != Variable('name', 'ref')
    assert var != Variable('name123123', 'ref')
    var_2 = Variable('name', 'ref')
    var_2.set_value('1234567')
    assert var == var_2


def test_variable_reference_strings_are_equal():
    """Check that reference_strings_are_equal works as expected."""
    assert Variable('name', 'ref').reference_strings_are_equal(Variable('name', 'qwe')) is False
    assert Variable('name', 'ref').reference_strings_are_equal(Variable('name', 'ref')) is True
    assert Variable('name', 'ref').reference_strings_are_equal(Variable('123123', 'ref')) is True
    assert Variable('name', 'ref').reference_strings_are_equal(Variable('123123', 'qweqwe')) is False


def test_variable_string_matches_variable():
    """Check that you can check if a string would become the same variable if used as a name."""
    assert Variable('name', 'my_ref').string_matches_variable('name') is True
    assert Variable('1', 'my_ref').string_matches_variable('1') is True
    assert Variable('!asd', 'my_ref').string_matches_variable('asd') is True
    assert Variable('!_____a', 'my_ref').string_matches_variable('_____a') is True


def test_variable_clean_reference_string():
    """Check that clean_reference_string and that is actually cleans the reference string."""
    assert Variable('name', 'myref').clean_reference_string == 'myref'
    assert Variable('name', 'order_asdasdasd').clean_reference_string == 'order'
    assert Variable('name', '§§§asd_asdasd').clean_reference_string == 'asd'


def test_variable_name():
    """Check that the name of the variable is generated correctly."""
    assert Variable('name', 'myref').name == 'name'
    assert Variable('123name', 'myref').name == 'name'
    assert Variable('12', 'myref').name == 'myref_1'
    assert Variable('!"§)!"(§&/$', 'myref').name == ''
    assert Variable('!"§)!"(§&/$123', 'myref').name == ''
    assert Variable('1!"§)!"(§&/$123', 'myref').name == 'myref_1'
