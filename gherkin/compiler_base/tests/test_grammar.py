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


def test_grammar_validation():
    """Check if different input to grammar is handled correctly."""
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


def test_grammar_chain():
    """Check that the grammar handles a chain as a rule correctly."""
    class MyNonTerminal(NonTerminal):
        criterion_terminal_symbol = TerminalSymbol(EOFToken)
        rule = Chain([
            TerminalSymbol(EOFToken),
            TerminalSymbol(EndOfLineToken),
            TerminalSymbol(FeatureToken),
        ])

    grammar = MyNonTerminal()
    # valid input
    grammar.validate_sequence(token_sequence([EOFToken(None), EndOfLineToken(None), FeatureToken('', None)]))

    # some other grammar that does not fit this
    assert_callable_raises(
        grammar.validate_sequence,
        NonTerminalNotUsed,
        args=[token_sequence([FeatureToken('', None), DescriptionToken('', None)])]   # <- criterion_terminal_symbol missing
    )

    # the grammar is not valid
    assert_callable_raises(
        grammar.validate_sequence,
        NonTerminalInvalid,
        args=[token_sequence([EOFToken(None), EndOfLineToken(None), EOFToken(None)])]      # <- grammar not complete
    )
    assert_callable_raises(
        grammar.validate_sequence,
        NonTerminalInvalid,
        args=[token_sequence([EOFToken(None), EOFToken(None), EOFToken(None)])]  # <- grammar not complete
    )


def test_grammar_nested():
    """Check what happens if a grammars are nested."""
    class NestedNonTerminal(NonTerminal):
        criterion_terminal_symbol = TerminalSymbol(DescriptionToken)
        rule = Chain([
            TerminalSymbol(DescriptionToken),
            TerminalSymbol(EndOfLineToken),
        ])

    nested_grammar = NestedNonTerminal()

    class ParentNonTerminal(NonTerminal):
        criterion_terminal_symbol = TerminalSymbol(FeatureToken)
        rule = Chain([
            TerminalSymbol(FeatureToken),
            nested_grammar,
            TerminalSymbol(EOFToken),
        ])

    grammar = ParentNonTerminal()

    # valid input
    grammar.validate_sequence(token_sequence([FeatureToken('', None), DescriptionToken('', None), EndOfLineToken(None), EOFToken(None)]))

    # grammar of parent not used
    error = assert_callable_raises(
        grammar.validate_sequence,
        NonTerminalNotUsed,
        args=[token_sequence([EOFToken(None)])],
    )
    assert error.grammar == grammar

    # grammar of child not used, so the grammar of the parent is not valid
    error = assert_callable_raises(
        grammar.validate_sequence,
        NonTerminalInvalid,
        args=[token_sequence([FeatureToken('', None), EOFToken(None)])],
    )
    assert error.grammar == grammar
