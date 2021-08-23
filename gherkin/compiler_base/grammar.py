from gherkin.compiler_base.symbol.non_terminal import NonTerminal
from gherkin.compiler_base.recursive import RecursiveValidationContainer


class Grammar(RecursiveValidationContainer):
    start_non_terminal: NonTerminal = None

    def __init__(self):
        assert self.start_non_terminal is not None, 'You must provide a starting NonTerminal object'
        assert isinstance(self.start_non_terminal, NonTerminal), 'The start of a grammar must be a NonTerminal.'

    def get_child_validator(self):
        return self.start_non_terminal

    def to_ebnf(self, ebnf_entries=None):
        """
        Returns the EBNF for this grammar. It will create a list and starts the process in its starting non terminal.
        """
        ebnf_entries = []
        self.start_non_terminal.to_ebnf(ebnf_entries)

        # EBNF is always presented in reversed order
        return '\n'.join(reversed(ebnf_entries))
