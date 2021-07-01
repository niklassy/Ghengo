class ExtractionError(Exception):
    """Indicates the the extractor had trouble to get a value."""
    def __init__(self, code):
        self.code = code
