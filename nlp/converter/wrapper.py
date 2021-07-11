class ConverterInitArgumentWrapper:
    """
    This class is used in converters to have an instance that holds a representative for a __init__ argument
    (e.g. a field from a model) and a token. The token was used to find the representative.
    """
    def __init__(self, token, representative):
        self.token = token
        self.representative = representative
