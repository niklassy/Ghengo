from gherkin.compiler.rule import Optional, RuleAlias, RuleToken, Grammar, Chain, GrammarInvalid, RuleNotFulfilled, \
    SequenceNotFinished, OneOf, Repeatable
from gherkin.compiler.token import Description, EndOfLine, EOF, Feature
from test_utils import assert_callable_raises


class RuleTestToken(RuleToken):
    def get_place_to_search(self) -> str:
        return ''


def token_sequence(sequence):
    return [RuleTestToken(t) for t in sequence]


def test_repeatable_invalid_input():
    """Check if invalid input to Repeatable is handled."""
    assert_callable_raises(Repeatable, ValueError, args=(Description,))
    assert_callable_raises(
        Repeatable,
        ValueError,
        args=(Optional(RuleAlias(Description)),),
        message='You must not use Optional as a child of Repeatable. Use minimum=0 instead.',
    )
    assert_callable_raises(Repeatable, ValueError, args=([RuleAlias(Description)],))


def test_repeatable_rule_alias():
    """Check if repeatable handles RuleAlias correctly."""
    repeatable = Repeatable(RuleAlias(EOF))
    repeatable.validate_sequence(token_sequence([EOF(None), EOF(None), EOF(None)]))
    assert_callable_raises(repeatable.validate_sequence, RuleNotFulfilled, args=[token_sequence([])])

    repeatable = Repeatable(RuleAlias(EOF), minimum=0)
    repeatable.validate_sequence(token_sequence([EOF(None), EOF(None), EOF(None)]))
    repeatable.validate_sequence(token_sequence([]))


def test_repeatable_chain():
    """Check that Repeatable handles Chains correctly as children."""
    repeatable = Repeatable(Chain([RuleAlias(EOF), RuleAlias(EndOfLine)]))
    # 1 & 2 repetitions
    repeatable.validate_sequence(token_sequence([EOF(None), EndOfLine(None)]))
    repeatable.validate_sequence(token_sequence([EOF(None), EndOfLine(None), EOF(None), EndOfLine(None)]))

    # minimum = 1, so this is no allowed
    assert_callable_raises(repeatable.validate_sequence, RuleNotFulfilled, args=[token_sequence([])])

    # chain is not valid
    assert_callable_raises(
        repeatable.validate_sequence,
        RuleNotFulfilled,
        args=[token_sequence([EndOfLine(None)])]
    )
    assert_callable_raises(
        repeatable.validate_sequence,
        RuleNotFulfilled,
        args=[token_sequence([EOF(None), EOF(None)])]
    )

    # one repetition is valid, then it ends and it is not handled
    assert_callable_raises(
        repeatable.validate_sequence,
        SequenceNotFinished,
        args=[token_sequence([EOF(None), EndOfLine(None), EndOfLine(None)])]
    )

    repeatable = Repeatable(Chain([RuleAlias(EOF), RuleAlias(EndOfLine)]), minimum=0)
    repeatable.validate_sequence(token_sequence([]))
    repeatable.validate_sequence(token_sequence([EOF(None), EndOfLine(None)]))
    repeatable.validate_sequence(token_sequence([EOF(None), EndOfLine(None), EOF(None), EndOfLine(None)]))


def test_repeatable_one_of():
    """Check that Repeatable handles OneOf correctly as a child."""
    repeatable = Repeatable(OneOf([
        RuleAlias(EOF),
        RuleAlias(EndOfLine),
    ]))
    # several valid repetitions
    repeatable.validate_sequence(token_sequence([EOF(None), EOF(None), EndOfLine(None), EOF(None)]))
    repeatable.validate_sequence(token_sequence([EndOfLine(None), EOF(None)]))
    repeatable.validate_sequence(token_sequence([EndOfLine(None), EndOfLine(None), EndOfLine(None)]))
    repeatable.validate_sequence(token_sequence([EOF(None), EOF(None)]))

    # check empty input and too long input
    assert_callable_raises(repeatable.validate_sequence, RuleNotFulfilled, args=[token_sequence([])])
    assert_callable_raises(
        repeatable.validate_sequence,
        SequenceNotFinished,
        args=[token_sequence([EOF(None), Feature('', None)])]
    )

    # do the same thing but with no minimum
    repeatable = Repeatable(OneOf([
        RuleAlias(EOF),
        RuleAlias(EndOfLine),
    ]), minimum=0)
    repeatable.validate_sequence(token_sequence([]))
    repeatable.validate_sequence(token_sequence([EOF(None), EOF(None)]))
    repeatable.validate_sequence(token_sequence([EndOfLine(None), EOF(None)]))
    repeatable.validate_sequence(token_sequence([EndOfLine(None), EndOfLine(None), EndOfLine(None)]))


def test_repeatable_grammar():
    """Check that Repeatable handles Grammar objects as children correctly."""
    class MyGrammar(Grammar):
        criterion_rule_alias = RuleAlias(EOF)
        rule = Chain([
            criterion_rule_alias,
            RuleAlias(EndOfLine),
        ])

    repeatable = Repeatable(MyGrammar())
    # valid values
    repeatable.validate_sequence(token_sequence([EOF(None), EndOfLine(None), EOF(None), EndOfLine(None)]))
    repeatable.validate_sequence(token_sequence([EOF(None), EndOfLine(None)]))

    # grammar recognized but no valid in first and second round
    assert_callable_raises(
        repeatable.validate_sequence,
        GrammarInvalid,
        args=[token_sequence([EOF(None), EOF(None)])],  # <- second EOF incorrect
    )
    assert_callable_raises(
        repeatable.validate_sequence,
        GrammarInvalid,
        args=[token_sequence([EOF(None), EndOfLine(None), EOF(None)])],     # <- incomplete
    )
    assert_callable_raises(
        repeatable.validate_sequence,
        GrammarInvalid,
        args=[token_sequence([EOF(None), EndOfLine(None), EOF(None), Feature('', None)])],  # <- Feature not correct
    )
