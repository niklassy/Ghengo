from nlp.generate.mixin import TemplateMixin
from nlp.generate.replaceable import Replaceable
from settings import INDENT_SPACES


class Argument(Replaceable, TemplateMixin):
    """
    Class that represents the values that are passed to a function during runtime.

    foo(a, "b", 1)
    => a, "b" and 1 are arguments.
    """
    template = '{value}'

    def __init__(self, value):
        super().__init__()
        self.value = value

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

    @classmethod
    def get_string_for_template(cls, string):
        return '\'{}\''.format(string) if isinstance(string, str) else str(string)

    def get_template_context(self, line_indent, indent):
        return {'value': self.value}


class _NestedArgument(Argument):
    start_symbol = ''
    end_symbol = ''

    def get_template_context(self, line_indent, indent):
        if len(str(self.value)) <= 100:
            value = self.value
        else:
            children = [Argument(value) for value in self.value]
            child_template = ',\n'.join(argument.to_template(
                line_indent + INDENT_SPACES, line_indent + INDENT_SPACES) for argument in children)

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


class SetArgument(_NestedArgument):
    start_symbol = '{'
    end_symbol = '}'


class StringArgument(Argument):
    def get_template_context(self, line_indent, indent):
        return {'value': '\'{}\''.format(self.value)}


class Kwarg(TemplateMixin):
    template = '{name}={value}'

    def __init__(self, name, value):
        super().__init__()
        self.name = name
        self.value = Argument(value)

    def get_template_context(self, line_indent, indent):
        return {'name': self.name, 'value': self.value.to_template(line_indent, 0)}
