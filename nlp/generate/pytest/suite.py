from nlp.generate.settings import GenerationSettings
from nlp.generate.suite import TestCaseBase, TestSuiteBase


class PyTestTestCase(TestCaseBase):
    replacement_for = TestCaseBase
    for_test_type = GenerationSettings.TestTypes.PY_TEST
    template = '{decorators}{decorator_separator}def {name}({parameters}):\n{statements}'


class PyTestTestSuite(TestSuiteBase):
    replacement_for = TestCaseBase
    for_test_type = GenerationSettings.TestTypes.PY_TEST
    template = '{imports}{warning_collection}{separator}{test_cases}\n'
    test_case_class = PyTestTestCase
