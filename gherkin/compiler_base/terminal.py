from gherkin.compiler_base.exception import SequenceEnded, RuleNotFulfilled
from gherkin.compiler_base.mixin import IndentMixin
from gherkin.compiler_base.recursive import RecursiveValidationBase


class TerminalSymbol(IndentMixin, RecursiveValidationBase):
    """
    This is a wrapper for defining rules. It is a wrapper around any custom class that is used while defining
    rules. For this project, the class could be removed, but it is a nice wrapper for future usage.
    """
    def __init__(self, token_cls):
        super().__init__()
        self.token_cls = token_cls

    def get_next_valid_tokens(self):
        return [self.token_cls]

    def sequence_to_object(self, sequence, index=0):
        """This alias represents a simple token - so just return at the index that we are at."""
        # everything is validated before this is called, so this should always be the same!
        assert sequence[index].token.__class__ == self.token_cls

        return sequence[index]

    def token_wrapper_is_valid(self, token_wrapper) -> bool:
        """
        Check if a given token_wrapper belongs to the class that this wrapper represents. Used by rules to check if a
        value is valid for this class.
        """
        return isinstance(token_wrapper.token, self.token_cls)

    def get_next_pointer_index(self, child, sequence, current_index) -> int:
        return current_index + 1

    def get_keywords(self) -> [str]:
        """
        Return a list of keywords. Used by rules to see what keywords are expected. So: what is expected to be found
        for this class? How can this token be represented as a string?
        """
        return self.token_cls.get_keywords()

    def _build_error_message(self, token_wrapper=None, message=''):
        """Builds the message for RuleNotFulfilled and SequenceEnded exceptions."""
        keywords = self.get_keywords()

        if len(keywords) == 1:
            message += 'Expected {}.'.format(keywords[0])
        elif len(keywords) > 1:
            message += 'Expected one of: {}.'.format(', '.join(['"{}"'.format(k) for k in keywords]))

        if token_wrapper:
            if not keywords:
                message += '{} is invalid. {}'.format(token_wrapper.get_text(), token_wrapper.get_place_to_search())
            else:
                message += ' Got {} instead. {}'.format(token_wrapper.get_text(), token_wrapper.get_place_to_search())

        return message

    def _validate_sequence(self, sequence, index):
        try:
            token_wrapper = sequence[index]
        except IndexError:
            message = self._build_error_message(message='Input ended abruptely. ')

            raise SequenceEnded(
                message,
                terminal_symbol=self,
                sequence_index=index,
                rule=self,
                suggested_tokens=self.get_next_valid_tokens(),
            )

        from gherkin.compiler_base.wrapper import TokenWrapper
        assert isinstance(token_wrapper, TokenWrapper)

        if not self.token_wrapper_is_valid(token_wrapper):
            message = self._build_error_message(token_wrapper)

            raise RuleNotFulfilled(
                message,
                terminal_symbol=self,
                sequence_index=index,
                rule=self,
                suggested_tokens=self.get_next_valid_tokens(),
            )

        # --- everything is valid from here on -----
        self.on_token_wrapper_valid(token_wrapper)

        return self.get_next_pointer_index(child=None, sequence=sequence, current_index=index)

    def on_token_wrapper_valid(self, token_wrapper):
        token_wrapper.token.set_grammar_meta_value('suggested_indent_level', self.get_suggested_indent_level())

    def __str__(self):
        return str(self.token_cls)

    def __eq__(self, other):
        if not isinstance(other, self.__class__):
            return False
        return self.token_cls == other.token_cls
