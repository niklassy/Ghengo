from gherkin.compiler_base.non_terminal import NonTerminal
from gherkin.compiler_base.recursive import RecursiveValidationBase


class Grammar(RecursiveValidationBase):
    start_non_terminal = None

    def __init__(self):
        assert self.start_non_terminal is not None
        assert isinstance(self.start_non_terminal, NonTerminal)

    def get_start_non_terminal(self) -> RecursiveValidationBase:
        return self.start_non_terminal

    def get_next_pointer_index(self, child, sequence, current_index) -> int:
        return self.get_start_non_terminal().get_next_pointer_index(child, sequence, current_index)

    def sequence_to_object(self, sequence, index=0):
        return self.get_start_non_terminal().sequence_to_object(sequence, index)

    def _validate_sequence(self, sequence, index) -> int:
        return self.get_start_non_terminal()._validate_sequence(sequence, index)

    def validate_sequence(self, sequence, index=0):
        return self.get_start_non_terminal().validate_sequence(sequence, index)

    def convert(self, sequence):
        return self.get_start_non_terminal().convert(sequence)
