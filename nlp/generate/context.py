from generate.utils import remove_non_alnum, to_function_name


class VariableContext(object):
    def __init__(self, source_token, variable_name_predetermined, reference_string):
        self.source_token = source_token
        self.reference_string = reference_string
        self.variable_name_predetermined = variable_name_predetermined

    def name_matches_variable(self, name):
        return self.variable_name == self.get_variable_name(name)

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
    def variable_name(self):
        return self.get_variable_name(self.variable_name_predetermined)
