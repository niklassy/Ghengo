from nlp.generate.mixin import TemplateMixin
from nlp.generate.settings import INDENT_SPACES


class Argument(TemplateMixin):
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

    def get_template_context(self, parent_intend):
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
            for arg in children:
                arg.indent = parent_intend + INDENT_SPACES

            child_template = ',\n'.join(argument.to_template(parent_intend) for argument in children)

            value = '{start_symbol}\n{child}\n{base_indent}{end_symbol}'.format(
                start_symbol=start_symbol,
                end_symbol=end_symbol,
                base_indent=self.get_indent_string(parent_intend),
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

    def get_template_context(self, parent_intend):
        return {'name': self.name, 'value': self.value}
