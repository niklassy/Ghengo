import mimetypes

from nlp.generate.argument import Argument, Kwarg
from nlp.generate.constants import CompareChar
from nlp.generate.mixin import TemplateMixin, OnAddToTestCaseListenerMixin
from nlp.generate.replaceable import Replaceable
from nlp.generate.variable import Variable
from core.settings import PYTHON_INDENT_SPACES
from nlp.generate.statement import Statement
from nlp.generate.suite import Import, ImportPlaceholder
from nlp.generate.utils import camel_to_snake_case


class Expression(Replaceable, TemplateMixin, OnAddToTestCaseListenerMixin):
    template = '{child}'

    def __init__(self, child=None):
        super().__init__()
        self.child = child
        assert not isinstance(child, Variable), 'You must not use Variable as a child of Expression. ' \
                                                'Use VariableReference instead'

    def get_template_context(self, line_indent, at_start_of_line):
        return {'child': self.child if self.child else ''}

    def get_children(self):
        return [self.child] if self.child else []

    def as_statement(self):
        """Expressions can be statements. This can be used to translate an expression into a Statement."""
        return Statement(self)


class FunctionCallExpression(Expression):
    template = '{fn_name}({long_content_start}{kwargs}{long_content_end})'

    def __init__(self, function_name, function_kwargs):
        super().__init__()
        self.function_name = function_name
        self.function_kwargs = function_kwargs

        for kwarg in function_kwargs:
            assert not isinstance(kwarg, Variable), 'You must not use Variable as function kwarg. Use' \
                                                    ' VariableReference instead'

    def get_children(self):
        references = super().get_children()
        return references + [self.function_name] + self.function_kwargs

    def get_template_context(self, line_indent, at_start_of_line):
        kwargs_template = ', '.join(
            [kwarg.to_template(line_indent, at_start_of_line=False) for kwarg in self.function_kwargs]
        )

        if len(str(self.function_name) + kwargs_template) > 100:
            long_content_start = '\n'
            long_content_end = '\n' + self.get_indent_string(line_indent)
            kwargs_template = ',\n'.join([kwarg.to_template(
                line_indent + PYTHON_INDENT_SPACES, at_start_of_line=True) for kwarg in self.function_kwargs])
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
    template = '{variable_ref}.{fn_name}()'

    def __init__(self, variable_ref):
        self.variable_ref = variable_ref
        assert not isinstance(variable_ref, Variable), 'You must not use Variable as variable_ref. Use' \
                                                       ' VariableReference instead'
        super().__init__('save', [])

    def get_children(self):
        return [self.variable_ref]

    def get_template_context(self, line_indent, at_start_of_line):
        context = super().get_template_context(line_indent, 0)
        context['variable_ref'] = self.variable_ref
        return context


class ModelQuerysetBaseExpression(FunctionCallExpression):
    def __init__(self, model_wrapper, function_name, function_kwargs):
        self.model_wrapper = model_wrapper
        super().__init__('{}.objects.{}'.format(model_wrapper.name, function_name), function_kwargs)

    def get_template_context(self, line_indent, at_start_of_line):
        context = super().get_template_context(line_indent, at_start_of_line)
        context['model'] = self.model_wrapper.name
        return context

    def on_add_to_test_case(self, test_case):
        super().on_add_to_test_case(test_case)

        # We can only add the import if the model already exists in the code
        if self.model_wrapper.exists_in_code:
            test_case.test_suite.add_import(
                Import(
                    self.model_wrapper.model.__module__,
                    self.model_wrapper.model.__name__
                )
            )
        else:
            test_case.test_suite.add_import(ImportPlaceholder(self.model_wrapper.name))


class ModelQuerysetFilterExpression(ModelQuerysetBaseExpression):
    def __init__(self, model_wrapper, function_kwargs):
        super().__init__(model_wrapper, 'filter', function_kwargs)


class ModelQuerysetGetExpression(ModelQuerysetBaseExpression):
    def __init__(self, model_wrapper, function_kwargs):
        super().__init__(model_wrapper, 'get', function_kwargs)


class ModelQuerysetAllExpression(ModelQuerysetBaseExpression):
    def __init__(self, model_wrapper):
        super().__init__(model_wrapper, 'all', [])


class CompareExpression(Expression):
    template = '{value_1} {compare_char} {value_2}'

    def __init__(self, value_1, compare_char, value_2):
        super().__init__()
        self.value_1 = value_1
        self.value_2 = value_2
        assert compare_char in CompareChar.get_all()
        self.compare_char = compare_char

    def get_children(self):
        references = super().get_children()
        return references + [self.value_1, self.value_2]

    def get_template_context(self, line_indent, at_start_of_line):
        return {'compare_char': self.compare_char, 'value_1': self.value_1, 'value_2': self.value_2}


class APIClientExpression(FunctionCallExpression):
    def __init__(self):
        super().__init__('APIClient', [])

    def on_add_to_test_case(self, test_case):
        super().on_add_to_test_case(test_case)

        test_case.test_suite.add_import(Import('rest_framework.test', 'APIClient'))


class APIClientAuthenticateExpression(FunctionCallExpression):
    def __init__(self, client_variable_ref, user_variable_ref):
        assert not isinstance(client_variable_ref, Variable), 'You must not use Variable as client_ref. Use' \
                                                              ' VariableReference instead'
        self.client_variable_ref = client_variable_ref
        super().__init__('{}.force_authenticate'.format(client_variable_ref), [Argument(user_variable_ref)])

    def get_children(self):
        references = super().get_children()
        return references + [self.client_variable_ref]


class ReverseCallExpression(FunctionCallExpression):
    template = '{fn_name}({reverse_name}{kwargs})'

    def __init__(self, reverse_name, reverse_kwargs):
        super().__init__('reverse', reverse_kwargs)
        self.reverse_name = Argument(reverse_name)

    def get_children(self):
        references = super().get_children()
        return references + [self.reverse_name]

    def get_template_context(self, line_indent, at_start_of_line):
        context = super().get_template_context(line_indent, at_start_of_line)
        context['reverse_name'] = self.reverse_name.to_template(line_indent, at_start_of_line=False)

        if len(self.function_kwargs) > 0:
            dict_content_str = ', '.join(['\'{}\': {}'.format(k.name, k.value) for k in self.function_kwargs])
            context['kwargs'] = ', {' + dict_content_str + '}'
        else:
            context['kwargs'] = ''

        return context


class RequestExpression(FunctionCallExpression):
    template = '{client_variable_ref}.{fn_name}({long_content_start}{reverse}{kwargs}{long_content_end})'

    def __init__(self, function_name, function_kwargs, reverse_name, client_variable_ref, reverse_kwargs, action_wrapper):
        super().__init__(function_name, function_kwargs)
        assert not isinstance(client_variable_ref, Variable), 'You must not use Variable as client_ref. Use' \
                                                              ' VariableReference instead'
        self.client_variable_ref = client_variable_ref
        self.reverse_expression = ReverseCallExpression(reverse_name, reverse_kwargs)
        self.action_wrapper = action_wrapper

    def get_children(self):
        references = super().get_children()
        return references + [self.client_variable_ref, self.reverse_expression]

    @property
    def serializer_class(self):
        return self.action_wrapper.serializer_cls

    def get_template_context(self, line_indent, at_start_of_line):
        context = super().get_template_context(line_indent, at_start_of_line)

        context['reverse'] = self.reverse_expression.to_template(line_indent, at_start_of_line=False)
        dict_content_str = ', '.join(
            ['\'{}\': {}'.format(
                k.name, k.value.to_template(line_indent, at_start_of_line=False)) for k in self.function_kwargs])

        # add `,` because it is an argument as well
        context['kwargs'] = ', {' + dict_content_str + '}' if dict_content_str else ''
        context['client_variable_ref'] = self.client_variable_ref
        return context

    def on_add_to_test_case(self, test_case):
        super().on_add_to_test_case(test_case)

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
        super().on_add_to_test_case(test_case)

        test_case.test_suite.add_import(Import('django.core.files.uploadedfile', 'SimpleUploadedFile'))


class ModelFactoryExpression(FunctionCallExpression):
    def __init__(self, model_wrapper, factory_kwargs):
        self.model_wrapper = model_wrapper
        super().__init__(self.factory_name, factory_kwargs)

    @property
    def factory_name(self):
        return '{}_factory'.format(camel_to_snake_case(self.model_wrapper.name))


class ModelM2MAddExpression(Expression):
    template = '{model_instance}.{field}.add({variable_ref})'

    def __init__(self, model_instance_variable_ref, field, add_variable_ref):
        super().__init__()
        assert not isinstance(model_instance_variable_ref, Variable), 'You must not use Variable as model. Use' \
                                                                      ' VariableReference instead'
        assert not isinstance(add_variable_ref, Variable), 'You must not use Variable as add var. Use' \
                                                           ' VariableReference instead'

        self.model_instance_variable_ref = model_instance_variable_ref
        self.field = field
        self.add_variable_ref = add_variable_ref

    def get_children(self):
        references = super().get_children()
        return references + [self.model_instance_variable_ref, self.add_variable_ref]

    def get_template_context(self, line_indent, at_start_of_line):
        variable_ref = self.add_variable_ref

        if isinstance(self.add_variable_ref, TemplateMixin):
            variable_ref = variable_ref.to_template(line_indent, at_start_of_line=False)

        return {
            'model_instance': self.model_instance_variable_ref,
            'field': self.field,
            'variable_ref': variable_ref,
        }
