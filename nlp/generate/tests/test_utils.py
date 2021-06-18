from nlp.generate.utils import camel_to_snake_case, to_function_name, remove_non_alnum, remove_non_ascii


def test_camel_to_snake_case():
    """Tests if camel_to_snake_case works as intended."""
    assert camel_to_snake_case('peterParker') == 'peter_parker'
    assert camel_to_snake_case('peterParker123') == 'peter_parker123'
    assert camel_to_snake_case('peterParker1/!"§)!"§/(') == 'peter_parker1'
    assert camel_to_snake_case('123"§$asd') == '123asd'
    assert camel_to_snake_case('ClassName') == 'class_name'


def test_to_function_name():
    """Check to_function_name transforms a string into a valid function name."""
    assert to_function_name('123asd') == 'asd'
    assert to_function_name('MyFunction123') == 'my_function123'
    assert to_function_name('MyFunction123%§$%') == 'my_function123'
    assert to_function_name('____foo') == '____foo'
    assert to_function_name('____12_foo') == '____12_foo'
    assert to_function_name('____12_fooBar') == '____12_foo_bar'
    assert to_function_name('____12_fooBär') == '____12_foo_bar'
    assert to_function_name('12____12_fooBär') == '____12_foo_bar'


def test_remove_non_alnum():
    """Check that remove_non_alnum removes all special characters and replaces them."""
    assert remove_non_alnum('123asd%%') == '123asd'
    assert remove_non_alnum('???123asd%%') == '123asd'
    assert remove_non_alnum('???123a!"§"§$"§$sd%%') == '123asd'
    assert remove_non_alnum('foo') == 'foo'
    assert remove_non_alnum('=foo?', replace_character='***') == '***foo***'


def test_remove_non_ascii():
    """Check that remove_non_ascii removes unusual characters and replaces them."""
    assert remove_non_ascii('aäüö') == 'aauo'
    assert remove_non_ascii('ßß') == 'ssss'
