
class RuleNotFulfilled(Exception):
    """
    This exception is raised when a a given sequence does not fulfill a rule.

    `terminal_symbol` -> The rule alias that is not fulfilled and resulted in an error.
    `sequence_index` -> the index in the sequence where the rule was broken
    `rule` -> the rule that was broken
    """
    def __init__(self, msg, terminal_symbol, sequence_index, comes_from, suggested_tokens):
        super().__init__(msg)
        self.terminal_symbol = terminal_symbol
        self.sequence_index = sequence_index
        self.comes_from = comes_from
        self.suggested_tokens = suggested_tokens


class NonTerminalInvalid(Exception):
    """
    An exception that is raised when a NonTerminal was detected but is not valid.
    """
    def __init__(self, msg, grammar, suggested_tokens):
        super().__init__(msg)
        self.grammar = grammar
        self.suggested_tokens = suggested_tokens


class SequenceEnded(Exception):
    """
    An exception that rules use to indicate that the given sequence has ended/ that the index has gone over
    the size of the sequence. This exception is only used internally.
    """

    def __init__(self, msg, terminal_symbol, sequence_index, comes_from, suggested_tokens):
        super().__init__(msg)
        self.terminal_symbol = terminal_symbol
        self.sequence_index = sequence_index
        self.comes_from = comes_from
        self.suggested_tokens = suggested_tokens


class NonTerminalNotUsed(Exception):
    """
    An exception that is raised when a NonTerminal is not used in a given sequence.
    """

    def __init__(self, msg, terminal_symbol, sequence_index, comes_from, grammar):
        super().__init__(msg)
        self.terminal_symbol = terminal_symbol
        self.sequence_index = sequence_index
        self.comes_from = comes_from
        self.grammar = grammar
        self.suggested_tokens = grammar.get_next_valid_tokens()


class SequenceNotFinished(Exception):
    """
    An exception that is raised when a given sequence was not fully checked at the end of validation.
    That usually means that there should be an item to indicate the end of a grammar/ rule (like EOF or EndOfLine).
    """
    pass
