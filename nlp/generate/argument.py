from nlp.generate.mixin import TemplateMixin, OnAddToTestCaseListenerMixin
from nlp.generate.replaceable import Replaceable
from nlp.generate.variable import Variable
from core.settings import PYTHON_INDENT_SPACES


class Argument(OnAddToTestCaseListenerMixin, Replaceable, TemplateMixin):
    """
    Class that represents the values that are passed to a function during runtime.

    foo(a, "b", 1)
    => a, "b" and 1 are arguments.
    """
    template = '{value}'

    def __init__(self, value):
        super().__init__()
        self.value = value
        assert not isinstance(value, Variable), 'You must not use a Variable with an Argument. Use a ' \
                                                'VariableReference instead'

    def __bool__(self):
        return bool(self.value)

    def __new__(cls, value, *args, **kwargs):
        if isinstance(value, list):
            return super().__new__(ListArgument, value, *args, **kwargs)

        if isinstance(value, set):
            return super().__new__(SetArgument, value, *args, **kwargs)

        if isinstance(value, tuple):
            return super().__new__(TupleArgument, value, *args, **kwargs)

        if isinstance(value, str):
            return super().__new__(StringArgument, value, *args, **kwargs)

        return super().__new__(cls, value, *args, **kwargs)

    def get_children(self):
        return [self.value]

    @classmethod
    def get_string_for_template(cls, string):
        return '\'{}\''.format(string) if isinstance(string, str) else str(string)

    def get_template_context(self, line_indent, at_start_of_line):
        value = self.value.to_template(line_indent, False) if isinstance(self.value, TemplateMixin) else self.value
        return {'value': value}


class _NestedArgument(Argument):
    start_symbol = ''
    end_symbol = ''
    force_comma = False

    def get_template_context(self, line_indent, at_start_of_line):
        if len(str(self.value)) <= 100:
            value = self.start_symbol

            for i, v in enumerate(self.value):
                if isinstance(v, TemplateMixin):
                    value += v.to_template(line_indent, False)
                else:
                    value += self.get_string_for_template(v)

                if i < len(self.value) - 1:
                    value += ', '
                elif self.force_comma:
                    value += ','

            value += self.end_symbol
        else:
            children = [Argument(value) for value in self.value]
            child_template = ',\n'.join(argument.to_template(
                line_indent + PYTHON_INDENT_SPACES, at_start_of_line=True) for argument in children)

            value = '{start_symbol}\n{child}\n{base_indent}{end_symbol}'.format(
                start_symbol=self.start_symbol,
                end_symbol=self.end_symbol,
                base_indent=self.get_indent_string(line_indent),
                child=child_template,
            )

        return {'value': value}


class ListArgument(_NestedArgument):
    start_symbol = '['
    end_symbol = ']'


class TupleArgument(_NestedArgument):
    start_symbol = '('
    end_symbol = ')'
    force_comma = True


class SetArgument(_NestedArgument):
    start_symbol = '{'
    end_symbol = '}'


class StringArgument(Argument):
    def get_template_context(self, line_indent, at_start_of_line):
        return {'value': '\'{}\''.format(self.value)}


class Kwarg(OnAddToTestCaseListenerMixin, TemplateMixin):
    template = '{name}={value}'

    def __init__(self, name, value):
        super().__init__()
        self.name = name
        self.value = Argument(value)

    def get_children(self):
        return [self.value]

    def get_template_context(self, line_indent, at_start_of_line):
        return {'name': self.name, 'value': self.value.to_template(line_indent, at_start_of_line=False)}
