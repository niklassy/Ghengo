from gherkin.compiler_base.exception import NonTerminalInvalid, RuleNotFulfilled, SequenceNotFinished
from gherkin.compiler_base.symbol.non_terminal import NonTerminal
from gherkin.compiler_base.rule.operator import Optional, Chain, OneOf, Repeatable
from gherkin.compiler_base.symbol.terminal import TerminalSymbol
from gherkin.compiler_base.wrapper import TokenWrapper
from gherkin.token import DescriptionToken, EndOfLineToken, EOFToken, FeatureToken, Token
from test_utils import assert_callable_raises


class CustomTokenWrapper(TokenWrapper):
    def get_place_to_search(self) -> str:
        return ''


def token_sequence(sequence):
    assert all([isinstance(t, Token) for t in sequence])
    return [CustomTokenWrapper(t) for t in sequence]


def test_one_of_invalid_input():
    """Check if invalid input to optional is handled."""
    assert_callable_raises(OneOf, ValueError, args=(DescriptionToken,))
    assert_callable_raises(OneOf, ValueError, args=([Optional(TerminalSymbol(EOFToken))],))
    assert_callable_raises(OneOf, ValueError, args=([Repeatable(TerminalSymbol(EOFToken), minimum=0)],))
    assert_callable_raises(OneOf, ValueError, args=(TerminalSymbol(DescriptionToken),))


def test_one_of_terminal_symbol():
    """Check that a OneOf rule correctly checks RuleAlias."""
    optional = OneOf([TerminalSymbol(DescriptionToken), TerminalSymbol(EOFToken), TerminalSymbol(EndOfLineToken)])
    optional.validate_sequence(token_sequence([DescriptionToken('', None)]))
    optional.validate_sequence(token_sequence([EOFToken(None)]))
    optional.validate_sequence(token_sequence([EndOfLineToken(None)]))
    assert_callable_raises(optional.validate_sequence, RuleNotFulfilled, args=[[]])
    assert_callable_raises(optional.validate_sequence, RuleNotFulfilled, args=(token_sequence([FeatureToken('', None)]),))


def test_one_of_grammar():
    """Checks that OneOf correctly handles a list of grammars."""
    class TestNonTerminal(NonTerminal):
        criterion_terminal_symbol = TerminalSymbol(DescriptionToken)
        rule = Chain([criterion_terminal_symbol, TerminalSymbol(EndOfLineToken)])

    class Test2NonTerminal(NonTerminal):
        criterion_terminal_symbol = TerminalSymbol(FeatureToken)
        rule = Chain([criterion_terminal_symbol, TerminalSymbol(EndOfLineToken)])

    grammar_one_of = OneOf([TestNonTerminal(), Test2NonTerminal()])
    # grammar 1 is recognized and works
    grammar_one_of.validate_sequence(token_sequence([DescriptionToken('', None), EndOfLineToken(None)]))
    # grammar 2 is recognized and works
    grammar_one_of.validate_sequence(token_sequence([FeatureToken('', None), EndOfLineToken(None)]))
    # none of the grammars are recognized, so the rule is not fulfilled
    assert_callable_raises(
        grammar_one_of.validate_sequence,
        RuleNotFulfilled,
        args=[token_sequence([EOFToken(None), EndOfLineToken(None)])],
    )
    # grammar 1 is recognized and does not work
    assert_callable_raises(
        grammar_one_of.validate_sequence,
        NonTerminalInvalid,
        args=[token_sequence([DescriptionToken('', None), FeatureToken('', None)])],
    )
    # grammar 2 is recognized and does not work
    assert_callable_raises(
        grammar_one_of.validate_sequence,
        NonTerminalInvalid,
        args=[token_sequence([FeatureToken('', None), EOFToken(None)])],
    )


def test_one_of_grammar_and_terminal_symbol():
    """Checks that OneOf correctly handles a list of combination of grammars and rule aliases."""
    class TestNonTerminal(NonTerminal):
        criterion_terminal_symbol = TerminalSymbol(DescriptionToken)
        rule = Chain([criterion_terminal_symbol, TerminalSymbol(EndOfLineToken)])

    one_of = OneOf([TestNonTerminal(), TerminalSymbol(EOFToken)])
    # rule alias is valid
    one_of.validate_sequence(token_sequence([EOFToken(None)]))
    # both are not valid
    assert_callable_raises(one_of.validate_sequence, RuleNotFulfilled, args=[token_sequence([EndOfLineToken(None)])])
    # grammar is recognized and not valid
    assert_callable_raises(
        one_of.validate_sequence, NonTerminalInvalid, args=[token_sequence([DescriptionToken('', None), EOFToken(None)])])


def test_one_of_grammar_and_rules():
    """Checks that OneOf correctly handles a list of combination of grammars and other rules."""
    class TestNonTerminal(NonTerminal):
        criterion_terminal_symbol = TerminalSymbol(DescriptionToken)
        rule = Chain([criterion_terminal_symbol, TerminalSymbol(EndOfLineToken)])

    one_of = OneOf([TestNonTerminal(), OneOf([TerminalSymbol(EOFToken), TerminalSymbol(FeatureToken)])])
    # rule is valid
    one_of.validate_sequence(token_sequence([EOFToken(None)]))
    one_of.validate_sequence(token_sequence([FeatureToken('', None)]))
    # both are not valid
    assert_callable_raises(one_of.validate_sequence, RuleNotFulfilled, args=[token_sequence([EndOfLineToken(None)])])
    # grammar is recognized and not valid
    assert_callable_raises(
        one_of.validate_sequence, NonTerminalInvalid, args=[token_sequence([DescriptionToken('', None), EOFToken(None)])])


def test_one_of_chain():
    """Check that OneOf behaves as expected when combined with a Chain."""
    one_of = OneOf([
        Chain([TerminalSymbol(DescriptionToken), TerminalSymbol(EndOfLineToken)]),
        Chain([TerminalSymbol(FeatureToken), TerminalSymbol(EOFToken)]),
    ])
    assert_callable_raises(one_of.validate_sequence, RuleNotFulfilled, args=[[]])
    one_of.validate_sequence(token_sequence([DescriptionToken('', None), EndOfLineToken(None)]))
    one_of.validate_sequence(token_sequence([FeatureToken('', None), EOFToken(None)]))
    assert_callable_raises(
        one_of.validate_sequence,
        RuleNotFulfilled,
        args=[token_sequence([EOFToken(None), FeatureToken('', None)])]
    )
    assert_callable_raises(
        one_of.validate_sequence,
        RuleNotFulfilled,
        args=[token_sequence([EndOfLineToken(None), DescriptionToken('', None)])]
    )


def test_one_of_repeatable():
    """Check that OneOf behaves as wanted with Repeatable as a child."""
    one_of = OneOf([
        Repeatable(TerminalSymbol(DescriptionToken)),
        Repeatable(TerminalSymbol(FeatureToken)),
    ])

    # check both sequences
    one_of.validate_sequence(token_sequence([DescriptionToken('', None), DescriptionToken('', None), DescriptionToken('', None)]))
    one_of.validate_sequence(token_sequence([FeatureToken('', None), FeatureToken('', None)]))

    # check for empty sequence
    assert_callable_raises(one_of.validate_sequence, RuleNotFulfilled, args=[[]])
    # check if sequence suddenly stops
    assert_callable_raises(
        one_of.validate_sequence,
        SequenceNotFinished,
        args=[token_sequence([FeatureToken('', None), DescriptionToken('', None), DescriptionToken('', None)])]
    )
    # check if none of values match
    assert_callable_raises(
        one_of.validate_sequence,
        RuleNotFulfilled,
        args=[token_sequence([EOFToken(None), DescriptionToken('', None), DescriptionToken('', None)])]
    )
