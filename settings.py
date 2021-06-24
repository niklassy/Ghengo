# number of spaces for an indent in Python
INDENT_SPACES = 4


class GenerationType:
    PY_TEST = 'py_test'


class _Settings:
    """
    Settings that can/ will be changed during runtime and generation of code.
    """
    class Defaults:
        LANGUAGE = 'en'
        GENERATE_TEST_TYPE = GenerationType.PY_TEST

    language = Defaults.LANGUAGE
    generate_test_type = Defaults.GENERATE_TEST_TYPE

    def reset(self):
        """Reset the settings to the default values."""
        self.language = self.Defaults.LANGUAGE
        self.generate_test_type = self.Defaults.GENERATE_TEST_TYPE


Settings = _Settings()
