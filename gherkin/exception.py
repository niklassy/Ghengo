class GherkinInvalid(Exception):
    """Used by the GherkinToPyTestCompiler to show that the provided Gherkin is not valid."""
    def __init__(self, msg, non_terminal, suggested_tokens):
        super().__init__(msg)
        self.non_terminal = non_terminal
        self.suggested_tokens = suggested_tokens
