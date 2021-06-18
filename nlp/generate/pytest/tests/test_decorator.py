from nlp.generate.pytest.decorator import PyTestMarkDecorator, PyTestParametrizeDecorator, DjangoDBDecorator
from nlp.generate.pytest.suite import PyTestTestSuite


def test_pytest_mark_decorator():
    """Check that PyTestMarkDecorator adds pytest as an import."""
    suite = PyTestTestSuite('foo')
    test_case = suite.create_and_add_test_case('bar')
    dec = PyTestMarkDecorator('baz')
    assert len(suite.imports) == 0
    dec.on_add_to_test_case(test_case)
    assert len(suite.imports) == 1
    assert suite.imports[0].path == 'pytest'


def test_pytest_parametrize_decorator_context():
    """Check the parametrize decorator generates the correct context."""
    dec = PyTestParametrizeDecorator(['arg_1', 'arg_2'], [(1, 2), (3, 4)])
    context = dec.get_template_context(0)
    assert context['decorator_name'] == 'pytest.mark.parametrize'
    assert context['arguments'] == '(\n    \'arg_1, arg_2\',\n    [(1, 2), (3, 4)]\n)'
    dec_2 = PyTestParametrizeDecorator([], [])
    context = dec_2.get_template_context(0)
    assert context['decorator_name'] == 'pytest.mark.parametrize'
    assert context['arguments'] == ''


def test_pytest_parametrize_decorator_on_add():
    """Check that the parametrize decorator adds a parameter to the test case."""
    suite = PyTestTestSuite('foo')
    test_case = suite.create_and_add_test_case('bar')
    dec = PyTestParametrizeDecorator(['arg_1', 'arg_2'], [(1, 2), (3, 4)])
    assert len(test_case.parameters) == 0
    dec.on_add_to_test_case(test_case)
    assert len(test_case.parameters) == 2
    assert test_case.parameters[0].name == 'arg_1'
    assert test_case.parameters[1].name == 'arg_2'
    dec.on_add_to_test_case(test_case)
    assert len(test_case.parameters) == 2
    assert test_case.parameters[0].name == 'arg_1'
    assert test_case.parameters[1].name == 'arg_2'


def test_pytest_django_db_decorator():
    """Check that the DjangoDBDecorator has the correct name."""
    assert DjangoDBDecorator().name == 'pytest.mark.django_db'
