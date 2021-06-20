from nlp.generate.expression import ModelFactoryExpression, FunctionCallExpression
from nlp.generate.importer import Importer
from nlp.generate.parameter import Parameter
from nlp.generate.pytest.decorator import DjangoDBDecorator
from nlp.generate.pytest.suite import PY_TEST


class PyTestModelFactoryExpression(ModelFactoryExpression):
    def on_add_to_test_case(self, test_case):
        parameter = Parameter(self.factory_name)
        try:
            test_case.add_parameter(parameter)
        except test_case.ParameterAlreadyPresent:
            pass

        # when a factory is used, there needs to be a mark for DjangoDB
        try:
            test_case.add_decorator(DjangoDBDecorator())
        except test_case.DecoratorAlreadyPresent:
            pass


class FixtureFunctionCallExpression(FunctionCallExpression):
    def on_add_to_test_case(self, test_case):
        try:
            test_case.add_parameter(Parameter(self.function_name))
        except test_case.ParameterAlreadyPresent:
            pass


Importer.register(PyTestModelFactoryExpression, ModelFactoryExpression, PY_TEST)
