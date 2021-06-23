from nlp.generate.mixin import TemplateMixin, OnAddToTestCaseListenerMixin
from nlp.generate.settings import INDENT_SPACES
from nlp.generate.statement import Statement
from nlp.generate.suite import Import
from nlp.generate.utils import camel_to_snake_case


class Expression(TemplateMixin, OnAddToTestCaseListenerMixin):
    def as_statement(self):
        """Expressions can be statements. This can be used to translate an expression into a Statement."""
        return Statement(self)


class FunctionCallExpression(Expression):
    template = '{fn_name}({long_content_start}{kwargs}{long_content_end})'

    def __init__(self, function_name, function_kwargs):
        super().__init__()
        self.function_name = function_name
        self.function_kwargs = function_kwargs

    def get_template_context(self, line_indent, indent):
        kwargs_template = ', '.join([kwarg.to_template(line_indent) for kwarg in self.function_kwargs])

        if len(self.function_name + kwargs_template) > 100:
            long_content_start = '\n'
            long_content_end = '\n' + self.get_indent_string(line_indent)
            kwargs_template = ',\n'.join([kwarg.to_template(
                line_indent, line_indent + INDENT_SPACES) for kwarg in self.function_kwargs])
        else:
            long_content_start = ''
            long_content_end = ''

        return {
            'fn_name': self.function_name,
            'long_content_start': long_content_start,
            'long_content_end': long_content_end,
            'kwargs': kwargs_template,
        }


class ModelSaveExpression(FunctionCallExpression):
    template = '{variable}.{fn_name}()'

    def __init__(self, variable):
        self.variable = variable
        super().__init__('save', [])

    def get_template_context(self, line_indent, indent):
        context = super().get_template_context(line_indent, 0)
        context['variable'] = self.variable
        return context


class ModelQuerysetBaseExpression(FunctionCallExpression):
    def __init__(self, model_interface, function_name, function_kwargs):
        self.model_interface = model_interface
        super().__init__('{}.objects.{}'.format(model_interface.name, function_name), function_kwargs)

    def get_template_context(self, line_indent, indent):
        context = super().get_template_context(line_indent, indent)
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
        super().__init__()
        self.model_instance_variable = model_instance_variable
        self.field = field
        self.add_variable = add_variable

    def get_template_context(self, line_indent, indent):
        variable = self.add_variable

        if isinstance(self.add_variable, TemplateMixin):
            variable = variable.to_template(line_indent)

        return {
            'model_instance': self.model_instance_variable,
            'field': self.field,
            'variable': variable,
        }

    def on_add_to_test_case(self, test_case):
        if isinstance(self.add_variable, OnAddToTestCaseListenerMixin):
            self.add_variable.on_add_to_test_case(test_case)
