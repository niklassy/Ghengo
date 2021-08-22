from gherkin.compiler_base.exception import GrammarInvalid, RuleNotFulfilled, SequenceNotFinished
from gherkin.compiler_base.rule import Optional, Grammar, Chain, OneOf, Repeatable
from gherkin.compiler_base.terminal import TerminalSymbol
from gherkin.compiler_base.wrapper import TokenWrapper
from gherkin.token import DescriptionToken, EndOfLineToken, EOFToken, FeatureToken
from test_utils import assert_callable_raises


class CustomTokenWrapper(TokenWrapper):
    def get_place_to_search(self) -> str:
        return ''


def token_sequence(sequence):
    return [CustomTokenWrapper(t) for t in sequence]


def test_chain_invalid_input():
    """Check if invalid input to chain is handled."""
    assert_callable_raises(Chain, ValueError, args=(DescriptionToken,))
    assert_callable_raises(Chain, ValueError, args=(TerminalSymbol(DescriptionToken),))


def test_chain_terminal_symbol():
    """Check if chain handles RuleAlias correctly."""
    chain = Chain([
        TerminalSymbol(EndOfLineToken),
        TerminalSymbol(EOFToken),
    ])
    chain.validate_sequence(token_sequence([EndOfLineToken(None), EOFToken(None)]))
    assert_callable_raises(
        chain.validate_sequence,
        RuleNotFulfilled,
        args=[token_sequence([EndOfLineToken(None), FeatureToken('', None)])]
    )
    assert_callable_raises(
        chain.validate_sequence,
        RuleNotFulfilled,
        args=[token_sequence([EOFToken(None), EndOfLineToken(None)])]
    )


def test_chain_repeatable():
    """Check that Chain handles Repeatable as a child correctly."""
    chain = Chain([
        Repeatable(TerminalSymbol(EOFToken)),
        Repeatable(TerminalSymbol(EndOfLineToken), minimum=0),
    ])
    # first repeatable is valid
    chain.validate_sequence(token_sequence([EOFToken(None)]))
    chain.validate_sequence(token_sequence([EOFToken(None), EOFToken(None), EOFToken(None)]))

    # both repeatable are valid
    chain.validate_sequence(token_sequence([EOFToken(None), EOFToken(None), EOFToken(None), EndOfLineToken(None)]))

    # first repeatable is not valid
    assert_callable_raises(
        chain.validate_sequence,
        RuleNotFulfilled,
        args=[token_sequence([EndOfLineToken(None), EOFToken(None)])]
    )

    # first repeatable is valid, second is optional, so sequence is not finished
    assert_callable_raises(
        chain.validate_sequence,
        SequenceNotFinished,
        args=[token_sequence([EOFToken(None), FeatureToken('', None)])]
    )


def test_chain_one_of():
    """Check that Chain handles OneOf as a child correctly."""
    chain = Chain([
        OneOf([TerminalSymbol(EOFToken), TerminalSymbol(FeatureToken)]),
        OneOf([TerminalSymbol(EndOfLineToken), TerminalSymbol(EOFToken)]),
    ])

    # both one of are valid
    chain.validate_sequence(token_sequence([EOFToken(None), EOFToken(None)]))
    chain.validate_sequence(token_sequence([EOFToken(None), EndOfLineToken(None)]))
    chain.validate_sequence(token_sequence([FeatureToken('', None), EndOfLineToken(None)]))
    chain.validate_sequence(token_sequence([FeatureToken('', None), EOFToken(None)]))

    # first invalid
    assert_callable_raises(
        chain.validate_sequence,
        RuleNotFulfilled,
        args=[token_sequence([EndOfLineToken(None), EOFToken(None)])]
    )

    # second invalid
    assert_callable_raises(
        chain.validate_sequence,
        RuleNotFulfilled,
        args=[token_sequence([FeatureToken('', None), FeatureToken('', None)])]
    )

    # both invalid
    assert_callable_raises(
        chain.validate_sequence,
        RuleNotFulfilled,
        args=[token_sequence([EndOfLineToken(None), FeatureToken('', None)])]
    )


def test_chain_grammar():
    """Check that Chain handles Grammars as children correctly."""
    class Grammar1(Grammar):
        criterion_terminal_symbol = TerminalSymbol(DescriptionToken)
        rule = Chain([
            criterion_terminal_symbol,
            TerminalSymbol(EndOfLineToken),
        ])

    class Grammar2(Grammar):
        criterion_terminal_symbol = TerminalSymbol(EOFToken)
        rule = Chain([
            criterion_terminal_symbol,
            TerminalSymbol(EndOfLineToken),
        ])

    chain = Chain([Grammar1(), Grammar2()])
    # both valid
    chain.validate_sequence(token_sequence([DescriptionToken('', None), EndOfLineToken(None), EOFToken(None), EndOfLineToken(None)]))
    # grammar 1 recognized and invalid
    assert_callable_raises(
        chain.validate_sequence,
        GrammarInvalid,
        args=[token_sequence([DescriptionToken('', None), EOFToken(None)])]
    )
    # grammar 1 valid, grammar 2 recognized and invalid
    assert_callable_raises(
        chain.validate_sequence,
        GrammarInvalid,
        args=[token_sequence([DescriptionToken('', None), EndOfLineToken(None), EOFToken(None), EOFToken(None)])]
    )
    # grammar 1 not recognized
    assert_callable_raises(
        chain.validate_sequence,
        RuleNotFulfilled,
        args=[token_sequence([EOFToken(None)])]
    )
    # grammar 1 valid, grammar 2 not recognized
    assert_callable_raises(
        chain.validate_sequence,
        RuleNotFulfilled,
        args=[token_sequence([DescriptionToken('', None), EndOfLineToken(None), DescriptionToken('', None)])]
    )


def test_chain_optional():
    """Check that Chain handles Optional as a child correctly."""
    chain = Chain([
        TerminalSymbol(EOFToken),
        Optional(TerminalSymbol(EndOfLineToken)),
        TerminalSymbol(EOFToken),
        Optional(TerminalSymbol(EOFToken)),
    ])
    chain.validate_sequence(token_sequence([EOFToken(None), EOFToken(None)]))
    chain.validate_sequence(token_sequence([EOFToken(None), EndOfLineToken(None), EOFToken(None)]))
    chain.validate_sequence(token_sequence([EOFToken(None), EndOfLineToken(None), EOFToken(None), EOFToken(None)]))
    chain.validate_sequence(token_sequence([EOFToken(None), EOFToken(None), EOFToken(None)]))
