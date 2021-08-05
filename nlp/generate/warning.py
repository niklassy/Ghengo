from nlp.generate.mixin import TemplateMixin
from settings import PYTHON_INDENT_SPACES


NO_VALUE_FOUND_CODE = '001'
BOOLEAN_NO_SOURCE = '002'
VARIABLE_NOT_FOUND = '003'
PERMISSION_NOT_FOUND = '004'
DICT_AS_STRING = '005'
FILE_NOT_FOUND = '006'
NUMBER_ERROR = '007'

WARNING_MESSAGES = {
    NO_VALUE_FOUND_CODE: 'No value was found for this field. One reason might be that the field does not exist '
                         'on the model and therefore it is harder to determine the value of the field. You can try '
                         'to write the value after the field name. Like: `Given an order with a number "123"`.',
    BOOLEAN_NO_SOURCE: 'There was no source found to determine the value of the boolean field.',
    VARIABLE_NOT_FOUND: 'There should be a variable in this place, but nothing was found for it. Maybe you did '
                        'not define a variable for a reference or the value is not found. You could try to write '
                        'the variable reference in quotations. Like: `Given an order with the owner "Alice".`',
    PERMISSION_NOT_FOUND: 'No value was found for the permission. Please make sure that the permission exists and '
                          'is given in the format "{model}.{permission_name}" or as free text like "Can create orders"',
    DICT_AS_STRING: 'Because explaining nested structures can be hard to explained via normal language and extracted '
                    'right now you have to set the values for fields as strings. Like \'{"foo": 123}\'.',
    FILE_NOT_FOUND: 'There was no variable found that holds a file. Please create a file before trying to access it.',
    NUMBER_ERROR: 'There was an error extracting the number. Please enter it in manually.'
}


class GenerationWarningDescription(TemplateMixin):
    template = 'class GenerationWarning{code}:\n{text}\n\n{call}'

    def __init__(self, code):
        super().__init__()
        self.code = code

    def get_template_context(self, line_indent, indent):
        one_indent = self.get_indent_string(line_indent + PYTHON_INDENT_SPACES)
        two_indents = self.get_indent_string(line_indent + (PYTHON_INDENT_SPACES * 2))

        message = WARNING_MESSAGES[self.code]

        if len(message) > 90:
            message_lines = ['']
            for word in message.split():
                message_lines[-1] += '{} '.format(word)
                if len(message_lines[-1]) > 90:
                    message_lines.append('')
            join_str = ' \\\n{}'.format(self.get_indent_string(line_indent + PYTHON_INDENT_SPACES + 7))
            message = join_str.join('\'{}\''.format(line) for line in message_lines)
        else:
            message = '\'{}\''.format(message)

        return {
            'call': '{}def __new__(cls, *args, **kwargs):\n{}return \'\''.format(one_indent, two_indents),
            'code': self.code,
            'text': '{}TEXT = {}'.format(one_indent, message),
        }

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return self.code == other.code


class GenerationWarning(TemplateMixin):
    template = 'GenerationWarning{code}()'

    def __init__(self, code):
        super().__init__()
        self.code = code

    def get_template_context(self, line_indent, indent):
        return {'code': self.code}

    @classmethod
    def create_for_test_case(cls, code):
        return GenerationWarning(code)


class GenerationWarningCollection(TemplateMixin):
    def __init__(self):
        super().__init__()
        self.warnings = []

    def get_template(self):
        if len(self.warnings) == 0:
            return ''
        return '\n\n\n{warnings}'

    def get_template_context(self, line_indent, indent):
        return {'warnings': '\n'.join([w.to_template() for w in self.warnings])}

    def add_warning(self, code):
        warning = GenerationWarningDescription(code)
        if warning not in self.warnings:
            self.warnings.append(warning)
