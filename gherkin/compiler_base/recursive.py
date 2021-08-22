from gherkin.compiler_base.exception import SequenceEnded, RuleNotFulfilled, SequenceNotFinished


class RecursiveValidationBase(object):
    def sequence_to_object(self, sequence, index=0):
        """
        Defines how a sequence at a given index is transformed into an object.

        This function may return a RuleToken, None, [RuleToken] or a custom object.
        """
        raise NotImplementedError()

    def get_next_pointer_index(self, child, sequence, current_index) -> int:
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
