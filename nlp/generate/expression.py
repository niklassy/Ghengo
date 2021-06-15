from nlp.generate.mixin import TemplateMixin, OnAddToTestCaseListenerMixin
from nlp.generate.statement import Statement
from nlp.generate.utils import camel_to_snake_case


class Expression(TemplateMixin, OnAddToTestCaseListenerMixin):
    def as_statement(self):
        return Statement(self)


class FunctionCallExpression(Expression):
    template = '{fn_name}({kwargs})'

    def __init__(self, function_name, function_kwargs):
        self.function_name = function_name
        self.function_kwargs = function_kwargs

    def get_template_context(self, indent):
        return {
            'fn_name': self.function_name,
            'kwargs': ', '.join([kwarg.to_template(indent) for kwarg in self.function_kwargs]),
        }


class ModelFactoryExpression(FunctionCallExpression):
    def __init__(self, model_interface, factory_kwargs):
        self.model_interface = model_interface
        super().__init__(self.factory_name, factory_kwargs)

    @property
    def factory_name(self):
        return '{}_factory'.format(self.get_model_in_snake_case())

    def get_model_in_snake_case(self):
        return camel_to_snake_case(self.model_interface.name)


class ModelM2MAddExpression(Expression):
    template = '{model_instance}.{field}.add({variable})'

    def __init__(self, model, field, variable):
        self.model = model
        self.field = field
        self.variable = variable

    def get_template_context(self, indent):
        return {
            'model_instance': self.model,
            'field': self.field,
            'variable': self.variable,
        }
