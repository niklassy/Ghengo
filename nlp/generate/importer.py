class _Importer(object):
    """
    This importer can be used to differentiate between imports that are used differently in different test types.

    If a certain statement is only used in py.test instead of another specific statement, you can register it here.
    On runtime, this can be used to get that replacement via the `get_class` function.
    """
    def __init__(self):
        self.replacements = {}

    def get_class(self, generate_class, env_name):
        try:
            return self.replacements[env_name][generate_class]
        except KeyError:
            return generate_class

    def register(self, generate_class, replaces, env_name):
        if self.replacements.get(env_name) is None:
            self.replacements[env_name] = {}

        self.replacements[env_name][replaces] = generate_class


Importer = _Importer()
