class ReferenceTokenWrapper:
    """
    This class is used in converters to have an instance that holds a reference for a __init__ argument
    (e.g. a field from a model) and a token. The token was used to find the reference.
    """
    def __init__(self, token, reference, source_represents_output=False):
        self.token = token
        self.reference = reference
        self.source_represents_output = source_represents_output

    @property
    def identifier(self):
        try:
            return self.reference.name
        except AttributeError:
            return self.reference

    def __str__(self):
        return '[Reference: {}] <--> [Token: {}]'.format(self.reference, self.token)
