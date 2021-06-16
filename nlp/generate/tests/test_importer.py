from nlp.generate.importer import Importer


class MyClass:
    pass


class MyReplacement:
    pass


def test_importer():
    """Check that the importer uses replacements in the correct environment."""
    Importer.register(MyReplacement, MyClass, '__test__')
    assert Importer.get_class(MyClass, '__test__') == MyReplacement
    assert Importer.get_class(MyClass, '__some_other__') == MyClass
