class _Importer(object):
    """
    This importer can be used to differentiate between imports that are used differently in different test types.

    If a certain statement is only used in py.test instead of another specific statement, you can register it here.
    On runtime, this can be used to get that replacement via the `get_class` function.
    """
    def __init__(self):
        self.replacements = {}

    def get_class(self, generate_class, test_case):
        try:
            return self.replacements[test_case.type][generate_class]
        except KeyError:
            return generate_class

    def register(self, generate_class, replaces, test_case):
        if self.replacements.get(test_case) is None:
            self.replacements[test_case] = {}

        self.replacements[test_case][replaces] = generate_class


Importer = _Importer()
