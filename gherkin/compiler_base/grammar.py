from gherkin.compiler_base.symbol.non_terminal import NonTerminal
from gherkin.compiler_base.recursive import RecursiveValidationContainer


class Grammar(RecursiveValidationContainer):
    start_non_terminal: NonTerminal = None

    def __init__(self):
        assert self.start_non_terminal is not None, 'You must provide a starting NonTerminal object'
        assert isinstance(self.start_non_terminal, NonTerminal), 'The start of a grammar must be a NonTerminal.'

    def get_child_validator(self):
        return self.start_non_terminal
