from gherkin.compiler_base.exception import NonTerminalInvalid, NonTerminalNotUsed
from gherkin.compiler_base.symbol.non_terminal import NonTerminal
from gherkin.compiler_base.rule.operator import Optional, Chain, OneOf, Repeatable
from gherkin.compiler_base.symbol.terminal import TerminalSymbol
from gherkin.compiler_base.wrapper import TokenWrapper
from gherkin.token import DescriptionToken, EndOfLineToken, EOFToken, FeatureToken
from test_utils import assert_callable_raises


class CustomTokenWrapper(TokenWrapper):
    def get_place_to_search(self) -> str:
        return ''


def token_sequence(sequence):
    return [CustomTokenWrapper(t) for t in sequence]


def test_non_terminal_validation():
    """Check if different input to non_terminal is handled correctly."""
    class NonTerminal1(NonTerminal):
        rule = None

    class NonTerminal2(NonTerminal):
        rule = Repeatable(TerminalSymbol(EOFToken))

    class NonTerminal3(NonTerminal):
        rule = Optional(TerminalSymbol(EOFToken))

    class NonTerminal6(NonTerminal):
        rule = OneOf([TerminalSymbol(EOFToken)])

    class NonTerminal4(NonTerminal):
        criterion_terminal_symbol = EOFToken
        rule = Chain([TerminalSymbol(EOFToken)])

    class NonTerminal5(NonTerminal):
        criterion_terminal_symbol = Chain([TerminalSymbol(EOFToken)])
        rule = Chain([TerminalSymbol(EOFToken)])

    assert_callable_raises(NonTerminal1, ValueError)    # <- no rule provided
    NonTerminal2()
    NonTerminal3()
    assert_callable_raises(NonTerminal4, ValueError)    # <- criterion_terminal_symbol is not wrapped
    assert_callable_raises(NonTerminal5, ValueError)    # <- criterion_terminal_symbol is not a terminal
    NonTerminal6()


def test_non_terminal_chain():
    """Check that the non_terminal handles a chain as a rule correctly."""
    class MyNonTerminal(NonTerminal):
        criterion_terminal_symbol = TerminalSymbol(EOFToken)
        rule = Chain([
            TerminalSymbol(EOFToken),
            TerminalSymbol(EndOfLineToken),
            TerminalSymbol(FeatureToken),
        ])

    non_terminal = MyNonTerminal()
    # valid input
    non_terminal.validate_sequence(token_sequence([EOFToken(None), EndOfLineToken(None), FeatureToken('', None)]))

    # some other non_terminal that does not fit this
    assert_callable_raises(
        non_terminal.validate_sequence,
        NonTerminalNotUsed,
        args=[token_sequence([FeatureToken('', None), DescriptionToken('', None)])]   # <- criterion_terminal_symbol missing
    )

    # the non_terminal is not valid
    assert_callable_raises(
        non_terminal.validate_sequence,
        NonTerminalInvalid,
        args=[token_sequence([EOFToken(None), EndOfLineToken(None), EOFToken(None)])]      # <- non_terminal not complete
    )
    assert_callable_raises(
        non_terminal.validate_sequence,
        NonTerminalInvalid,
        args=[token_sequence([EOFToken(None), EOFToken(None), EOFToken(None)])]  # <- non_terminal not complete
    )


def test_non_terminal_nested():
    """Check what happens if a non_terminals are nested."""
    class NestedNonTerminal(NonTerminal):
        criterion_terminal_symbol = TerminalSymbol(DescriptionToken)
        rule = Chain([
            TerminalSymbol(DescriptionToken),
            TerminalSymbol(EndOfLineToken),
        ])

    nested_non_terminal = NestedNonTerminal()

    class ParentNonTerminal(NonTerminal):
        criterion_terminal_symbol = TerminalSymbol(FeatureToken)
        rule = Chain([
            TerminalSymbol(FeatureToken),
            nested_non_terminal,
            TerminalSymbol(EOFToken),
        ])

    non_terminal = ParentNonTerminal()

    # valid input
    non_terminal.validate_sequence(token_sequence([FeatureToken('', None), DescriptionToken('', None), EndOfLineToken(None), EOFToken(None)]))

    # non_terminal of parent not used
    error = assert_callable_raises(
        non_terminal.validate_sequence,
        NonTerminalNotUsed,
        args=[token_sequence([EOFToken(None)])],
    )
    assert error.non_terminal == non_terminal

    # non_terminal of child not used, so the non_terminal of the parent is not valid
    error = assert_callable_raises(
        non_terminal.validate_sequence,
        NonTerminalInvalid,
        args=[token_sequence([FeatureToken('', None), EOFToken(None)])],
    )
    assert error.non_terminal == non_terminal
