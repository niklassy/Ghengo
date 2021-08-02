from nlp.generate.warning import WARNING_MESSAGES


class ExtractionError(Exception):
    """Indicates the the extractor had trouble to get a value."""
    def __init__(self, code):
        self.code = code

    @property
    def generation_message(self):
        return WARNING_MESSAGES[self.code]

    def __repr__(self):
        return '{}: {}'.format(self.__class__.__class__, self.generation_message)
