from nlp.generate.replaceable import Replaceable
from nlp.generate.utils import to_function_name


class Variable(Replaceable):
    """
    This class represents a variable in a test case.
    """
    def __init__(self, name_predetermined, reference_string):
        self.reference_string = reference_string
        self.name_predetermined = name_predetermined
        self.value = None

    def __copy__(self):
        variable = Variable(
            name_predetermined=self.name_predetermined,
            reference_string=self.reference_string,
        )
        variable.set_value(self.value)
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
        """Create a copy of this variable."""
        return self.__copy__()

    def reference_strings_are_equal(self, variable):
        """
        Check if the reference strings from another variable and this one are equal.
        """
        return variable.clean_reference_string == self.clean_reference_string

    def set_value(self, value):
        """Set the value of the variable."""
        self.value = value

    def string_matches_variable(self, string):
        """
        Check if a string would result in this variable under the same circumstances / with the same reference string.
        """
        var_copy = self.copy()
        var_copy.name_predetermined = string

        return var_copy.name == self.name

    @property
    def clean_reference_string(self):
        """
        Returns the reference string and cleans it up so that it can be used in a function name.
        """
        first_underscore_index = self.reference_string.find('_')

        if first_underscore_index < 0:
            return to_function_name(self.reference_string)

        return to_function_name(self.reference_string[:first_underscore_index])

    @property
    def name(self):
        """
        Returns the name of the variable.
        """
        predetermined_name = self.name_predetermined
        clean_name = to_function_name(predetermined_name)

        if clean_name:
            return clean_name

        if predetermined_name and len(predetermined_name) > 0 and predetermined_name[0].isdigit():
            return '{}_{}'.format(self.clean_reference_string.lower(), predetermined_name[0])

        return ''
