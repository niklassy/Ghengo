from generate.utils import remove_non_alnum, to_function_name


class Variable(object):
    def __init__(self, name_predetermined, reference_string):
        self.reference_string = reference_string
        self.name_predetermined = name_predetermined
        self.value = None

    def __copy__(self):
        variable = Variable(
            name_predetermined=self.name_predetermined,
            reference_string=self.reference_string,
        )
        variable.value = self.value
        return variable

    def __bool__(self):
        return bool(self.name)

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return other.name == self.name and self.value == other.value

    def __str__(self):
        return self.name

    def copy(self):
        return self.__copy__()

    def has_similar_reference_string(self, variable):
        return variable.clean_reference_string == self.clean_reference_string

    def set_value(self, value):
        self.value = value

    def string_matches_variable(self, string):
        return self.name == self.get_variable_name(string)

    def get_variable_name(self, predetermined_name):
        clean_name = remove_non_alnum(predetermined_name) if predetermined_name else ''

        if not clean_name:
            return ''

        if clean_name[0].isalpha():
            return to_function_name(predetermined_name)

        # must be number
        return '{}_{}'.format(self.clean_reference_string.lower(), clean_name[0])

    @property
    def clean_reference_string(self):
        return self.reference_string[:self.reference_string.find('_')]

    @property
    def name(self):
        return self.get_variable_name(self.name_predetermined)
