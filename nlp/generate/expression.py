from nlp.generate.mixin import TemplateMixin, OnAddToTestCaseListenerMixin
from nlp.generate.statement import Statement
from nlp.generate.suite import Import
from nlp.generate.utils import camel_to_snake_case


class Expression(TemplateMixin, OnAddToTestCaseListenerMixin):
    def as_statement(self):
        """Expressions can be statements. This can be used to translate an expression into a Statement."""
        return Statement(self)


class FunctionCallExpression(Expression):
    template = '{fn_name}({kwargs})'

    def __init__(self, function_name, function_kwargs):
        self.function_name = function_name
        self.function_kwargs = function_kwargs

    def get_template_context(self, indent):
        return {
            'fn_name': self.function_name,
            'kwargs': ', '.join([kwarg.to_template() for kwarg in self.function_kwargs]),
        }


class ModelQuerysetBaseExpression(FunctionCallExpression):
    def __init__(self, model_interface, function_name, function_kwargs):
        self.model_interface = model_interface
        super().__init__('{}.objects.{}'.format(model_interface.name, function_name), function_kwargs)

    def get_template_context(self, indent):
        context = super().get_template_context(indent)
        context['model'] = self.model_interface.name
        return context

    def on_add_to_test_case(self, test_case):
        test_case.test_suite.add_import(Import('django.contrib.auth.models', 'Permission'))


class ModelQuerysetFilterExpression(ModelQuerysetBaseExpression):
    def __init__(self, model_interface, function_kwargs):
        super().__init__(model_interface, 'filter', function_kwargs)


class ModelFactoryExpression(FunctionCallExpression):
    def __init__(self, model_interface, factory_kwargs):
        self.model_interface = model_interface
        super().__init__(self.factory_name, factory_kwargs)

    @property
    def factory_name(self):
        return '{}_factory'.format(camel_to_snake_case(self.model_interface.name))


class ModelM2MAddExpression(Expression):
    template = '{model_instance}.{field}.add({variable})'

    def __init__(self, model_instance_variable, field, add_variable):
        self.model_instance_variable = model_instance_variable
        self.field = field
        self.add_variable = add_variable

    def get_template_context(self, indent):
        return {
            'model_instance': self.model_instance_variable,
            'field': self.field,
            'variable': self.add_variable,
        }

    def on_add_to_test_case(self, test_case):
        if isinstance(self.add_variable, OnAddToTestCaseListenerMixin):
            self.add_variable.on_add_to_test_case(test_case)
