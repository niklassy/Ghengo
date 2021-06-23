from nlp.generate.settings import GenerationSettings


class Replaceable(object):
    """
    Whatever inherits from this class is given the possibility that children can replace the instance of the parent.
    This can be useful when you want to use different classes depending on settings. In this case there might be
    some classes that we only want to use when we generate py.test code.
    """
    for_test_type = None
    replacement_for = None

    def __new__(cls, *args, **kwargs):
        for sub_class in cls.__subclasses__():
            if sub_class.replacement_for == cls and GenerationSettings.test_type == sub_class.for_test_type:
                return super().__new__(sub_class)

        return super().__new__(cls)
