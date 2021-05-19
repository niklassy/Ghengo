from gherkin.compiler_base.exception import GrammarInvalid, RuleNotFulfilled, SequenceNotFinished
from gherkin.compiler_base.rule import Optional, RuleAlias, TokenWrapper, Grammar, Chain, OneOf, Repeatable
from gherkin.token import DescriptionToken, EndOfLineToken, EOFToken, FeatureToken
from test_utils import assert_callable_raises


class TestTokenWrapper(TokenWrapper):
    def get_place_to_search(self) -> str:
        return ''


def token_sequence(sequence):
    return [TestTokenWrapper(t) for t in sequence]


def test_chain_invalid_input():
    """Check if invalid input to chain is handled."""
    assert_callable_raises(Chain, ValueError, args=(DescriptionToken,))
    assert_callable_raises(Chain, ValueError, args=(RuleAlias(DescriptionToken),))


def test_chain_rule_alias():
    """Check if chain handles RuleAlias correctly."""
    chain = Chain([
        RuleAlias(EndOfLineToken),
        RuleAlias(EOFToken),
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
        Repeatable(RuleAlias(EOFToken)),
        Repeatable(RuleAlias(EndOfLineToken), minimum=0),
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
        OneOf([RuleAlias(EOFToken), RuleAlias(FeatureToken)]),
        OneOf([RuleAlias(EndOfLineToken), RuleAlias(EOFToken)]),
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
        criterion_rule_alias = RuleAlias(DescriptionToken)
        rule = Chain([
            criterion_rule_alias,
            RuleAlias(EndOfLineToken),
        ])

    class Grammar2(Grammar):
        criterion_rule_alias = RuleAlias(EOFToken)
        rule = Chain([
            criterion_rule_alias,
            RuleAlias(EndOfLineToken),
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
        RuleAlias(EOFToken),
        Optional(RuleAlias(EndOfLineToken)),
        RuleAlias(EOFToken),
        Optional(RuleAlias(EOFToken)),
    ])
    chain.validate_sequence(token_sequence([EOFToken(None), EOFToken(None)]))
    chain.validate_sequence(token_sequence([EOFToken(None), EndOfLineToken(None), EOFToken(None)]))
    chain.validate_sequence(token_sequence([EOFToken(None), EndOfLineToken(None), EOFToken(None), EOFToken(None)]))
    chain.validate_sequence(token_sequence([EOFToken(None), EOFToken(None), EOFToken(None)]))
