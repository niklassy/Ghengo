from nlp.generate.suite import TestCaseBase, TestSuiteBase


class PyTestTestCase(TestCaseBase):
    template = '{decorators}{decorator_separator}def test_{name}({arguments}):\n{statements}'


class PyTestTestSuite(TestSuiteBase):
    template = '{imports}{separator}{test_cases}\n'
    test_case_class = PyTestTestCase
