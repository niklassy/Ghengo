from settings import Settings


class Replaceable(object):
    """
    Whatever inherits from this class is given the possibility that children can replace the instance of the parent.
    This can be useful when you want to use different classes depending on settings. In this case there might be
    some classes that we only want to use when we generate py.test code.
    """
    for_test_type = None
    replacement_for = None

    @classmethod
    def should_be_replaced(cls, sub_class):
        return sub_class.should_replace(cls) and Settings.GENERATE_TEST_TYPE == sub_class.for_test_type

    @classmethod
    def should_replace(cls, parent):
        return cls.replacement_for == parent

    def __new__(cls, *args, **kwargs):
        for sub_class in cls.__subclasses__():
            if cls.should_be_replaced(sub_class):
                return super().__new__(sub_class)

        return super().__new__(cls)
