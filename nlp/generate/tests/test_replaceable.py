from nlp.generate.replaceable import Replaceable
from settings import Settings


def test_replaceable_correct_test_type():
    """Check that if the circumstances are correct, a subclass of Replaceable is indeed replaced."""
    test_placeholder = 'THIS_IS_A_PLACEHOLDER'
    Settings.generate_test_type = test_placeholder

    class SubClass(Replaceable):
        pass

    class SubSubClass(SubClass):
        replacement_for = SubClass
        for_test_type = test_placeholder

    assert isinstance(SubClass(), SubSubClass)


def test_replaceable_incorrect_test_type():
    """Check that if the test type is not correct, the class is not replaced."""
    test_placeholder = 'THIS_IS_A_PLACEHOLDER'
    Settings.generate_test_type = test_placeholder

    class SubClass(Replaceable):
        pass

    class SubSubClass(SubClass):
        replacement_for = SubClass
        for_test_type = 'SOME_OTHER_TEST_TYPE'

    assert not isinstance(SubClass(), SubSubClass)
