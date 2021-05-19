from gherkin.compiler_base.exception import GrammarInvalid, RuleNotFulfilled, SequenceNotFinished
from gherkin.compiler_base.rule import Optional, RuleAlias, TokenWrapper, Grammar, Chain, OneOf, Repeatable
from gherkin.token import DescriptionToken, EndOfLineToken, EOFToken, FeatureToken
from test_utils import assert_callable_raises


class TestTokenWrapper(TokenWrapper):
    def get_place_to_search(self) -> str:
        return ''


def token_sequence(sequence):
    return [TestTokenWrapper(t) for t in sequence]


def test_repeatable_invalid_input():
    """Check if invalid input to Repeatable is handled."""
    assert_callable_raises(Repeatable, ValueError, args=(DescriptionToken,))
    assert_callable_raises(
        Repeatable,
        ValueError,
        args=(Optional(RuleAlias(DescriptionToken)),),
        message='You must not use Optional as a child of Repeatable. Use minimum=0 instead.',
    )
    assert_callable_raises(Repeatable, ValueError, args=([RuleAlias(DescriptionToken)],))


def test_repeatable_rule_alias():
    """Check if repeatable handles RuleAlias correctly."""
    repeatable = Repeatable(RuleAlias(EOFToken))
    repeatable.validate_sequence(token_sequence([EOFToken(None), EOFToken(None), EOFToken(None)]))
    assert_callable_raises(repeatable.validate_sequence, RuleNotFulfilled, args=[token_sequence([])])

    repeatable = Repeatable(RuleAlias(EOFToken), minimum=0)
    repeatable.validate_sequence(token_sequence([EOFToken(None), EOFToken(None), EOFToken(None)]))
    repeatable.validate_sequence(token_sequence([]))


def test_repeatable_chain():
    """Check that Repeatable handles Chains correctly as children."""
    repeatable = Repeatable(Chain([RuleAlias(EOFToken), RuleAlias(EndOfLineToken)]))
    # 1 & 2 repetitions
    repeatable.validate_sequence(token_sequence([EOFToken(None), EndOfLineToken(None)]))
    repeatable.validate_sequence(token_sequence([EOFToken(None), EndOfLineToken(None), EOFToken(None), EndOfLineToken(None)]))

    # minimum = 1, so this is no allowed
    assert_callable_raises(repeatable.validate_sequence, RuleNotFulfilled, args=[token_sequence([])])

    # chain is not valid
    assert_callable_raises(
        repeatable.validate_sequence,
        RuleNotFulfilled,
        args=[token_sequence([EndOfLineToken(None)])]
    )
    assert_callable_raises(
        repeatable.validate_sequence,
        RuleNotFulfilled,
        args=[token_sequence([EOFToken(None), EOFToken(None)])]
    )

    # one repetition is valid, then it ends and it is not handled
    assert_callable_raises(
        repeatable.validate_sequence,
        SequenceNotFinished,
        args=[token_sequence([EOFToken(None), EndOfLineToken(None), EndOfLineToken(None)])]
    )

    repeatable = Repeatable(Chain([RuleAlias(EOFToken), RuleAlias(EndOfLineToken)]), minimum=0)
    repeatable.validate_sequence(token_sequence([]))
    repeatable.validate_sequence(token_sequence([EOFToken(None), EndOfLineToken(None)]))
    repeatable.validate_sequence(token_sequence([EOFToken(None), EndOfLineToken(None), EOFToken(None), EndOfLineToken(None)]))


def test_repeatable_one_of():
    """Check that Repeatable handles OneOf correctly as a child."""
    repeatable = Repeatable(OneOf([
        RuleAlias(EOFToken),
        RuleAlias(EndOfLineToken),
    ]))
    # several valid repetitions
    repeatable.validate_sequence(token_sequence([EOFToken(None), EOFToken(None), EndOfLineToken(None), EOFToken(None)]))
    repeatable.validate_sequence(token_sequence([EndOfLineToken(None), EOFToken(None)]))
    repeatable.validate_sequence(token_sequence([EndOfLineToken(None), EndOfLineToken(None), EndOfLineToken(None)]))
    repeatable.validate_sequence(token_sequence([EOFToken(None), EOFToken(None)]))

    # check empty input and too long input
    assert_callable_raises(repeatable.validate_sequence, RuleNotFulfilled, args=[token_sequence([])])
    assert_callable_raises(
        repeatable.validate_sequence,
        SequenceNotFinished,
        args=[token_sequence([EOFToken(None), FeatureToken('', None)])]
    )

    # do the same thing but with no minimum
    repeatable = Repeatable(OneOf([
        RuleAlias(EOFToken),
        RuleAlias(EndOfLineToken),
    ]), minimum=0)
    repeatable.validate_sequence(token_sequence([]))
    repeatable.validate_sequence(token_sequence([EOFToken(None), EOFToken(None)]))
    repeatable.validate_sequence(token_sequence([EndOfLineToken(None), EOFToken(None)]))
    repeatable.validate_sequence(token_sequence([EndOfLineToken(None), EndOfLineToken(None), EndOfLineToken(None)]))


def test_repeatable_grammar():
    """Check that Repeatable handles Grammar objects as children correctly."""
    class MyGrammar(Grammar):
        criterion_rule_alias = RuleAlias(EOFToken)
        rule = Chain([
            criterion_rule_alias,
            RuleAlias(EndOfLineToken),
        ])

    repeatable = Repeatable(MyGrammar())
    # valid values
    repeatable.validate_sequence(token_sequence([EOFToken(None), EndOfLineToken(None), EOFToken(None), EndOfLineToken(None)]))
    repeatable.validate_sequence(token_sequence([EOFToken(None), EndOfLineToken(None)]))

    # grammar recognized but no valid in first and second round
    assert_callable_raises(
        repeatable.validate_sequence,
        GrammarInvalid,
        args=[token_sequence([EOFToken(None), EOFToken(None)])],  # <- second EOF incorrect
    )
    assert_callable_raises(
        repeatable.validate_sequence,
        GrammarInvalid,
        args=[token_sequence([EOFToken(None), EndOfLineToken(None), EOFToken(None)])],     # <- incomplete
    )
    assert_callable_raises(
        repeatable.validate_sequence,
        GrammarInvalid,
        args=[token_sequence([EOFToken(None), EndOfLineToken(None), EOFToken(None), FeatureToken('', None)])],  # <- Feature not correct
    )

    assert_callable_raises(
        repeatable.validate_sequence,
        RuleNotFulfilled,
        args=[token_sequence([DescriptionToken('', None)])]
    )
