class ConverterProperty:
    """
    While converters have a specific algorithm to find interesting tokens for stuff like model fields,
    that algorithm does not work for specific cases. This class is used whenever a converter needs to find
    very specific stuff, e.g. the name of a model in a text.

    This class holds three values:
        - the noun chunk where the token should be
        - the token that represents what we are searching for
        - the value that the token translates to

    These values are cached and determined when fetching the value for the first time. The converter can use these
    values in its instance over and over again.

    This class is an extension to converters. It acts as a more complicated property with more data and more power.
    This class also allows re-usage over multiple converters if they need the same stuff (e.g. finding the model).
    """
    def __init__(self, converter):
        self.converter = converter
        self.document = converter.document
        self._chunk = None
        self.chunk_determined = False
        self._token = None
        self.token_determined = False
        self._value = None
        self.value_determined = False

    def __str__(self):
        return '{}-Property; Chunk {}; Token {}; value: {}'.format(
            self.converter.__class__.__name__, self.chunk, self.token, self.value)

    def reset_cache(self):
        self.chunk_determined = False
        self.value_determined = False
        self.token_determined = False

    def get_chunk(self):
        raise NotImplementedError()

    def calculate_chunk(self):
        """
        This function can be used to calculate the value. It can be useful in cases where a property has to be
        determined before another one.
        """
        return self.chunk

    @property
    def chunk(self):
        """The chunk in which the token can be found."""
        if self.chunk_determined is False:
            self._chunk = self.get_chunk()
            self.chunk_determined = True
        return self._chunk

    def get_token(self):
        raise NotImplementedError()

    def calculate_token(self):
        """
        This function can be used to calculate the token. It can be useful in cases where a property has to be
        determined before another one.
        """
        return self.token

    @property
    def token(self):
        """The token that represents something."""
        if self.token_determined is False:
            self._token = self.get_token()
            self.token_determined = True
        return self._token

    def get_value(self):
        raise NotImplementedError()

    def calculate_value(self):
        """
        This function can be used to calculate the value. It can be useful in cases where a property has to be
        determined before another one.
        """
        return self.value

    @property
    def value(self):
        """The value that is determined from the token or the chunk."""
        if self.value_determined is False:
            self._value = self.get_value()
            self.value_determined = True
        return self._value
