import inspect
import mimetypes

from nlp.generate.argument import Argument, Kwarg
from nlp.generate.constants import CompareChar
from nlp.generate.mixin import TemplateMixin, OnAddToTestCaseListenerMixin, ReferencedVariablesMixin
from nlp.generate.replaceable import Replaceable
from settings import PYTHON_INDENT_SPACES
from nlp.generate.statement import Statement
from nlp.generate.suite import Import, ImportPlaceholder
from nlp.generate.utils import camel_to_snake_case


class Expression(ReferencedVariablesMixin, Replaceable, TemplateMixin, OnAddToTestCaseListenerMixin):
    template = '{child}'

    def __init__(self, child=None):
        self.child = child

    def get_template_context(self, line_indent, indent):
        return {'child': self.child if self.child else ''}

    def as_statement(self):
        """Expressions can be statements. This can be used to translate an expression into a Statement."""
        return Statement(self)


class FunctionCallExpression(Expression):
    template = '{fn_name}({long_content_start}{kwargs}{long_content_end})'

    def __init__(self, function_name, function_kwargs):
        super().__init__()
        self.function_name = function_name
        self.function_kwargs = function_kwargs

    def get_variable_reference_children(self):
        references = super().get_variable_reference_children()
        return references + [self.function_name] + self.function_kwargs

    def get_template_context(self, line_indent, indent):
        kwargs_template = ', '.join([kwarg.to_template(line_indent) for kwarg in self.function_kwargs])

        if len(str(self.function_name) + kwargs_template) > 100:
            long_content_start = '\n'
            long_content_end = '\n' + self.get_indent_string(line_indent)
            kwargs_template = ',\n'.join([kwarg.to_template(
                line_indent, line_indent + PYTHON_INDENT_SPACES) for kwarg in self.function_kwargs])
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

    def get_variable_reference_children(self):
        return [self.variable]

    def get_template_context(self, line_indent, indent):
        context = super().get_template_context(line_indent, 0)
        context['variable'] = self.variable
        return context


class ModelQuerysetBaseExpression(FunctionCallExpression):
    def __init__(self, model_adapter, function_name, function_kwargs):
        self.model_adapter = model_adapter
        super().__init__('{}.objects.{}'.format(model_adapter.name, function_name), function_kwargs)

    def get_template_context(self, line_indent, indent):
        context = super().get_template_context(line_indent, indent)
        context['model'] = self.model_adapter.name
        return context

    def on_add_to_test_case(self, test_case):
        # We can only add the import if the model already exists in the code
        if self.model_adapter.exists_in_code:
            test_case.test_suite.add_import(
                Import(
                    self.model_adapter.model.__module__,
                    self.model_adapter.model.__name__
                )
            )
        else:
            test_case.test_suite.add_import(ImportPlaceholder(self.model_adapter.name))


class ModelQuerysetFilterExpression(ModelQuerysetBaseExpression):
    def __init__(self, model_adapter, function_kwargs):
        super().__init__(model_adapter, 'filter', function_kwargs)


class ModelQuerysetGetExpression(ModelQuerysetBaseExpression):
    def __init__(self, model_adapter, function_kwargs):
        super().__init__(model_adapter, 'get', function_kwargs)


class ModelQuerysetAllExpression(ModelQuerysetBaseExpression):
    def __init__(self, model_adapter):
        super().__init__(model_adapter, 'all', [])


class CompareExpression(Expression):
    template = '{value_1} {compare_char} {value_2}'

    def __init__(self, value_1, compare_char, value_2):
        super().__init__()
        self.value_1 = value_1
        self.value_2 = value_2
        assert compare_char in CompareChar.get_all()
        self.compare_char = compare_char

    def get_variable_reference_children(self):
        references = super().get_variable_reference_children()
        return references + [self.value_1, self.value_2]

    def get_template_context(self, line_indent, indent):
        return {'compare_char': self.compare_char, 'value_1': self.value_1, 'value_2': self.value_2}


class APIClientExpression(FunctionCallExpression):
    def __init__(self):
        super().__init__('APIClient', [])

    def on_add_to_test_case(self, test_case):
        test_case.test_suite.add_import(Import('rest_framework.test', 'APIClient'))


class APIClientAuthenticateExpression(FunctionCallExpression):
    def __init__(self, client_variable, user_variable):
        self.client_variable = client_variable
        super().__init__('{}.force_authenticate'.format(client_variable), [Argument(user_variable)])

    def get_variable_reference_children(self):
        references = super().get_variable_reference_children()
        return references + [self.client_variable]


class ReverseCallExpression(FunctionCallExpression):
    template = '{fn_name}({reverse_name}{kwargs})'

    def __init__(self, reverse_name, reverse_kwargs):
        super().__init__('reverse', reverse_kwargs)
        self.reverse_name = Argument(reverse_name)

    def get_variable_reference_children(self):
        references = super().get_variable_reference_children()
        return references + [self.reverse_name]

    def get_template_context(self, line_indent, indent):
        context = super().get_template_context(line_indent, indent)
        context['reverse_name'] = self.reverse_name.to_template(line_indent, 0)

        if len(self.function_kwargs) > 0:
            dict_content_str = ', '.join(['\'{}\': {}'.format(k.name, k.value) for k in self.function_kwargs])
            context['kwargs'] = ', {' + dict_content_str + '}'
        else:
            context['kwargs'] = ''

        return context


class RequestExpression(FunctionCallExpression):
    template = '{client_variable}.{fn_name}({long_content_start}{reverse}{kwargs}{long_content_end})'

    def __init__(self, function_name, function_kwargs, reverse_name, client_variable, reverse_kwargs, url_adapter):
        super().__init__(function_name, function_kwargs)
        self.client_variable = client_variable
        self.reverse_expression = ReverseCallExpression(reverse_name, reverse_kwargs)
        self.url_adapter = url_adapter

    def get_variable_reference_children(self):
        references = super().get_variable_reference_children()
        return references + [self.client_variable, self.reverse_expression]

    @property
    def serializer_class(self):
        return self.url_adapter.get_serializer_class(self.function_name)

    def get_template_context(self, line_indent, indent):
        context = super().get_template_context(line_indent, indent)

        context['reverse'] = self.reverse_expression.to_template(line_indent, 0)
        dict_content_str = ', '.join(
            ['\'{}\': {}'.format(k.name, k.value.to_template(line_indent)) for k in self.function_kwargs])

        # add `,` because it is an argument as well
        context['kwargs'] = ', {' + dict_content_str + '}' if dict_content_str else ''
        context['client_variable'] = self.client_variable
        return context

    def on_add_to_test_case(self, test_case):
        test_case.test_suite.add_import(Import('django.urls', 'reverse'))


class CreateUploadFileExpression(FunctionCallExpression):
    def __init__(self, function_kwargs):
        super().__init__('SimpleUploadedFile', function_kwargs)

        for kwarg in self.function_kwargs:
            self.add_kwarg(kwarg)

    def add_kwarg(self, kwarg):
        content_type_guesses = []

        if kwarg not in self.function_kwargs:
            self.function_kwargs.append(kwarg)

        if kwarg.name == 'name':
            # value of the kwarg is always an argument
            argument = kwarg.value
            content_type_guesses = mimetypes.MimeTypes().guess_type(argument.value)

        if len(content_type_guesses) > 0 and content_type_guesses[0]:
            self.function_kwargs.append(Kwarg('content_type', content_type_guesses[0]))

    def on_add_to_test_case(self, test_case):
        test_case.test_suite.add_import(Import('django.core.files.uploadedfile', 'SimpleUploadedFile'))


class ModelFactoryExpression(FunctionCallExpression):
    def __init__(self, model_adapter, factory_kwargs):
        self.model_adapter = model_adapter
        super().__init__(self.factory_name, factory_kwargs)

    @property
    def factory_name(self):
        return '{}_factory'.format(camel_to_snake_case(self.model_adapter.name))


class ModelM2MAddExpression(Expression):
    template = '{model_instance}.{field}.add({variable})'

    def __init__(self, model_instance_variable, field, add_variable):
        super().__init__()
        self.model_instance_variable = model_instance_variable
        self.field = field
        self.add_variable = add_variable

    def get_variable_reference_children(self):
        references = super().get_variable_reference_children()
        return references + [self.model_instance_variable, self.add_variable]

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
