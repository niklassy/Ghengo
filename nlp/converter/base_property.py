class ConverterProperty:
    """
    Converters have a pattern that repeats again and again: Finding a token, its chunk and the that is determined
    from that. The key difference to Extractors: extractors are changing on runtime. ConverterProperties are information
    the Converter MUST have in order to create statements. Extractors are additional information for these statements.
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

    @property
    def chunk(self):
        """The chunk in which the token can be found."""
        if self.chunk_determined is False:
            self._chunk = self.get_chunk()
            self.chunk_determined = True
        return self._chunk

    def get_token(self):
        raise NotImplementedError()

    @property
    def token(self):
        """The token that represents something."""
        if self.token_determined is False:
            self._token = self.get_token()
            self.token_determined = True
        return self._token

    def get_value(self):
        raise NotImplementedError()

    @property
    def value(self):
        """The value that is determined from the token or the chunk."""
        if self.value_determined is False:
            self._value = self.get_value()
            self.value_determined = True
        return self._value
