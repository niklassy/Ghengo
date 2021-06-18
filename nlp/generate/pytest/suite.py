from nlp.generate.suite import TestCaseBase, TestSuiteBase

PY_TEST = 'pytest'


class PyTestTestCase(TestCaseBase):
    template = '{decorators}{decorator_separator}def {name}({parameters}):\n{statements}'
    type = PY_TEST


class PyTestTestSuite(TestSuiteBase):
    template = '{imports}{warning_collection}{separator}{test_cases}\n'
    test_case_class = PyTestTestCase
    type = PY_TEST
