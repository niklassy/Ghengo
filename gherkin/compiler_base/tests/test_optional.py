from gherkin.compiler_base.exception import NonTerminalInvalid, RuleNotFulfilled, SequenceNotFinished
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


def test_optional_invalid_input():
    """Check if invalid input to optional is handled."""
    assert_callable_raises(Optional, ValueError, args=(DescriptionToken,))
    assert_callable_raises(Optional, ValueError, args=([TerminalSymbol(DescriptionToken)],))
    assert_callable_raises(Optional, ValueError, args=(Repeatable(TerminalSymbol(EOFToken)),))


def test_optional_terminal_symbol():
    """Check that an optional rule makes everything related to a rule alias pass."""
    # ======= validate a rule alias
    optional = Optional(TerminalSymbol(DescriptionToken))
    optional.validate_sequence(token_sequence([DescriptionToken('', None)]))
    optional.validate_sequence([])


def test_optional_grammar():
    """Check that an optional makes grammars pass if they are not used."""
    class CustomNonTerminal(NonTerminal):
        criterion_terminal_symbol = TerminalSymbol(DescriptionToken)
        rule = Chain([criterion_terminal_symbol, TerminalSymbol(EndOfLineToken)])

    optional = Optional(CustomNonTerminal())
    # the grammar is used, so the grammar should raise an error and Optional should not catch it
    assert_callable_raises(
        optional.validate_sequence,
        NonTerminalInvalid,
        args=(token_sequence([DescriptionToken('', None), DescriptionToken('', None)]),),
    )
    assert_callable_raises(
        optional.validate_sequence,
        SequenceNotFinished,
        args=(token_sequence([EOFToken(None), EOFToken(None)]),),
    )

    optional.validate_sequence(token_sequence([]))


def test_optional_chain():
    """Check that optional behaves as expected when combined with a Chain."""
    optional = Optional(Chain([
        TerminalSymbol(DescriptionToken),
        TerminalSymbol(EndOfLineToken),
    ]))
    optional.validate_sequence(token_sequence([]))
    optional.validate_sequence(token_sequence([DescriptionToken('', None), EndOfLineToken(None)]))

    assert_callable_raises(
        optional.validate_sequence,
        SequenceNotFinished,
        args=(token_sequence([EOFToken(None)]),)
    )


def test_optional_one_of():
    """Check that one of is correctly handled by Optional."""
    optional = Chain([
        Optional(OneOf([
            TerminalSymbol(DescriptionToken),
            TerminalSymbol(EndOfLineToken),
        ])),
        TerminalSymbol(EOFToken),
    ])
    optional.validate_sequence(token_sequence([EOFToken(None)]))
    optional.validate_sequence(token_sequence([DescriptionToken('', None), EOFToken(None)]))
    optional.validate_sequence(token_sequence([EndOfLineToken(None), EOFToken(None)]))

    assert_callable_raises(
        optional.validate_sequence,
        RuleNotFulfilled,
        args=(token_sequence([FeatureToken('', None), EOFToken(None)]),),
    )

