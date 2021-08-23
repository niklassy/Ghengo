from abc import ABC

from gherkin.compiler_base.exception import SequenceEnded, RuleNotFulfilled, SequenceNotFinished


class RecursiveValidationBase(object):
    """
    This is the base class that is used throughout the recursive parser to validate data and pass data around.
    """
    def to_ebnf(self, ebnf_entries=None):
        """
        This function can be used to get the definition as EBNF. ebnf_entries can be used to create additional
        entries that need to be handled later on.

        :argument: ebnf_entries: a list of strings that hold more entries
        :returns: a string that represents this object in EBNF
        """
        raise NotImplementedError()

    def sequence_to_object(self, sequence, index=0):
        """
        Defines how a sequence at a given index is transformed into an object.

        You should:
            - call `_validate_sequence` just to make sure that everything is fine
            - do everything that is needed to determine the object (like calling `get_next_pointer_index` again)
            - return the object by maybe calling `sequence_to_object` of the child

        This function may return a TerminalSymbol, None, [TerminalSymbol] or a custom object.
        """
        raise NotImplementedError()

    def get_next_pointer_index(self, child, sequence, current_index) -> int:
        """
        Returns the next index the pointer points to in the sequence.
        """
        raise NotImplementedError()

    def convert(self, sequence):
        """
        Can be called to convert a given sequence to an object. The returned object depends on the Rule.
        """
        self.validate_sequence(sequence)
        return self.sequence_to_object(sequence)

    def _validate_sequence(self, sequence, index) -> int:
        """
        Implemented by each child. Does the validation of a given sequence. Can be called recursively.
        The index represents the current index at which the sequence is checked.

        This should probably call `self.get_next_pointer_index` in some way to validate. It can also call
        `_validate_sequence` of its child.
        """
        raise NotImplementedError()

    def validate_sequence(self, sequence, index=0):
        """
        Public function to validate a given sequence. May raise a RuleNotFulfilled or a SequenceNotFinished.
        """
        from gherkin.compiler_base.wrapper import TokenWrapper
        assert all([isinstance(el, TokenWrapper) for el in sequence]), 'Every entry in the passed sequence must be of ' \
                                                                       'class "TokenWrapper"'

        try:
            result_index = self._validate_sequence(sequence, index)
        except SequenceEnded as e:
            raise RuleNotFulfilled(
                str(e),
                sequence_index=e.sequence_index,
                terminal_symbol=e.terminal_symbol,
                comes_from=e.comes_from,
                suggested_tokens=e.suggested_tokens,
            )

        if result_index < len(sequence):
            raise SequenceNotFinished()

        return result_index


class RecursiveValidationContainer(RecursiveValidationBase, ABC):
    """
    This is a base class that can be used to simply let a child handle the recursive validation. It will pass
    all functions to its child.
    """
    def get_child_validator(self) -> RecursiveValidationBase:
        """Return the child validator that will handle everything."""
        raise NotImplementedError()

    def get_next_pointer_index(self, child, sequence, current_index) -> int:
        return self.get_child_validator().get_next_pointer_index(child, sequence, current_index)

    def sequence_to_object(self, sequence, index=0):
        return self.get_child_validator().sequence_to_object(sequence, index)

    def _validate_sequence(self, sequence, index) -> int:
        return self.get_child_validator()._validate_sequence(sequence, index)

    def validate_sequence(self, sequence, index=0):
        return self.get_child_validator().validate_sequence(sequence, index)

    def convert(self, sequence):
        return self.get_child_validator().convert(sequence)
