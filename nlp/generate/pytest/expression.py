from nlp.generate.expression import ModelFactoryExpression
from nlp.generate.parameter import Parameter
from nlp.generate.pytest.decorator import DjangoDBDecorator


class PyTestModelFactoryExpression(ModelFactoryExpression):
    def on_add_to_test_case(self, test_case):
        parameter = Parameter(self.factory_name)
        test_case.add_parameter(parameter)

        # when a factory is used, there needs to be a mark for DjangoDB
        test_case.add_decorator(DjangoDBDecorator())
