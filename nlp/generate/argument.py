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

    @classmethod
    def get_string_for_template(cls, string):
        return '\'{}\''.format(string) if isinstance(string, str) else str(string)

    def get_template_context(self, line_indent, indent):
        if isinstance(self.value, (list, tuple, set)) and len(str(self.value)) > 100:
            if isinstance(self.value, list):
                start_symbol = '['
                end_symbol = ']'
            elif isinstance(self.value, tuple):
                start_symbol = '('
                end_symbol = ')'
            else:
                start_symbol = '{'
                end_symbol = '}'

            children = [Argument(value) for value in self.value]
            child_template = ',\n'.join(argument.to_template(
                line_indent + INDENT_SPACES, line_indent + INDENT_SPACES) for argument in children)

            value = '{start_symbol}\n{child}\n{base_indent}{end_symbol}'.format(
                start_symbol=start_symbol,
                end_symbol=end_symbol,
                base_indent=self.get_indent_string(line_indent),
                child=child_template,
            )
        else:
            value = self.get_string_for_template(self.value)

        return {'value': value}


class Kwarg(TemplateMixin):
    template = '{name}={value}'

    def __init__(self, name, value):
        super().__init__()
        self.name = name
        self.value = Argument(value)

    def get_template_context(self, line_indent, indent):
        return {'name': self.name, 'value': self.value.to_template(line_indent, indent)}
