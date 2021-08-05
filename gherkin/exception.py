class GherkinInvalid(Exception):
    """Used by the GherkinToPyTestCompiler to show that the provided Gherkin is not valid."""
    def __init__(self, msg, grammar):
        super().__init__(msg)
        self.grammar = grammar
