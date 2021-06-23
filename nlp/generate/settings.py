# number of spaces for an indent in Python
INDENT_SPACES = 4


class _GenerationSettings:
    class TestTypes:
        PY_TEST = 'py_test'

    DEFAULT_TEST_TYPE = TestTypes.PY_TEST
    test_type = DEFAULT_TEST_TYPE


GenerationSettings = _GenerationSettings()
