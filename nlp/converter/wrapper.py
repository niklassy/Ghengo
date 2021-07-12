class ConverterInitArgumentWrapper:
    """
    This class is used in converters to have an instance that holds a representative for a __init__ argument
    (e.g. a field from a model) and a token. The token was used to find the representative.
    """
    def __init__(self, token, representative, source_represents_output=False):
        self.token = token
        self.representative = representative
        self.source_represents_output = source_represents_output

    @property
    def identifier(self):
        try:
            return self.representative.name
        except AttributeError:
            return self.representative

    def __str__(self):
        return '[Representative: {}] <--> [Token: {}]'.format(self.representative, self.token)