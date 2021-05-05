from gherkin.compiler.rule import Optional, RuleAlias, RuleToken, Grammar, Chain, GrammarInvalid, RuleNotFulfilled, \
    SequenceNotFinished, OneOf, Repeatable
from gherkin.compiler.token import Description, EndOfLine, EOF, Feature
from test_utils import assert_callable_raises


class RuleTestToken(RuleToken):
    def get_place_to_search(self) -> str:
        return ''


def token_sequence(sequence):
    return [RuleTestToken(t) for t in sequence]


def test_chain_invalid_input():
    """Check if invalid input to chain is handled."""
    assert_callable_raises(Chain, ValueError, args=(Description,))
    assert_callable_raises(Chain, ValueError, args=(RuleAlias(Description),))


def test_chain_rule_alias():
    """Check if chain handles RuleAlias correctly."""
    chain = Chain([
        RuleAlias(EndOfLine),
        RuleAlias(EOF),
    ])
    chain.validate_sequence(token_sequence([EndOfLine(None), EOF(None)]))
    assert_callable_raises(
        chain.validate_sequence,
        RuleNotFulfilled,
        args=[token_sequence([EndOfLine(None), Feature('', None)])]
    )
    assert_callable_raises(
        chain.validate_sequence,
        RuleNotFulfilled,
        args=[token_sequence([EOF(None), EndOfLine(None)])]
    )


def test_chain_repeatable():
    """Check that Chain handles Repeatable as a child correctly."""
    chain = Chain([
        Repeatable(RuleAlias(EOF)),
        Repeatable(RuleAlias(EndOfLine), minimum=0),
    ])
    # first repeatable is valid
    chain.validate_sequence(token_sequence([EOF(None)]))
    chain.validate_sequence(token_sequence([EOF(None), EOF(None), EOF(None)]))

    # both repeatable are valid
    chain.validate_sequence(token_sequence([EOF(None), EOF(None), EOF(None), EndOfLine(None)]))

    # first repeatable is not valid
    assert_callable_raises(
        chain.validate_sequence,
        RuleNotFulfilled,
        args=[token_sequence([EndOfLine(None), EOF(None)])]
    )

    # first repeatable is valid, second is optional, so sequence is not finished
    assert_callable_raises(
        chain.validate_sequence,
        SequenceNotFinished,
        args=[token_sequence([EOF(None), Feature('', None)])]
    )


def test_chain_one_of():
    """Check that Chain handles OneOf as a child correctly."""
    chain = Chain([
        OneOf([RuleAlias(EOF), RuleAlias(Feature)]),
        OneOf([RuleAlias(EndOfLine), RuleAlias(EOF)]),
    ])

    # both one of are valid
    chain.validate_sequence(token_sequence([EOF(None), EOF(None)]))
    chain.validate_sequence(token_sequence([EOF(None), EndOfLine(None)]))
    chain.validate_sequence(token_sequence([Feature('', None), EndOfLine(None)]))
    chain.validate_sequence(token_sequence([Feature('', None), EOF(None)]))

    # first invalid
    assert_callable_raises(
        chain.validate_sequence,
        RuleNotFulfilled,
        args=[token_sequence([EndOfLine(None), EOF(None)])]
    )

    # second invalid
    assert_callable_raises(
        chain.validate_sequence,
        RuleNotFulfilled,
        args=[token_sequence([Feature('', None), Feature('', None)])]
    )

    # both invalid
    assert_callable_raises(
        chain.validate_sequence,
        RuleNotFulfilled,
        args=[token_sequence([EndOfLine(None), Feature('', None)])]
    )


def test_chain_grammar():
    """Check that Chain handles Grammars as children correctly."""
    class Grammar1(Grammar):
        criterion_rule_alias = RuleAlias(Description)
        rule = Chain([
            criterion_rule_alias,
            RuleAlias(EndOfLine),
        ])

    class Grammar2(Grammar):
        criterion_rule_alias = RuleAlias(EOF)
        rule = Chain([
            criterion_rule_alias,
            RuleAlias(EndOfLine),
        ])

    chain = Chain([Grammar1(), Grammar2()])
    # both valid
    chain.validate_sequence(token_sequence([Description('', None), EndOfLine(None), EOF(None), EndOfLine(None)]))
    # grammar 1 recognized and invalid
    assert_callable_raises(
        chain.validate_sequence,
        GrammarInvalid,
        args=[token_sequence([Description('', None), EOF(None)])]
    )
    # grammar 1 valid, grammar 2 recognized and invalid
    assert_callable_raises(
        chain.validate_sequence,
        GrammarInvalid,
        args=[token_sequence([Description('', None), EndOfLine(None), EOF(None), EOF(None)])]
    )
    # grammar 1 not recognized
    assert_callable_raises(
        chain.validate_sequence,
        RuleNotFulfilled,
        args=[token_sequence([EOF(None)])]
    )
    # grammar 1 valid, grammar 2 not recognized
    assert_callable_raises(
        chain.validate_sequence,
        RuleNotFulfilled,
        args=[token_sequence([Description('', None), EndOfLine(None), Description('', None)])]
    )


def test_chain_optional():
    """Check that Chain handles Optional as a child correctly."""
    chain = Chain([
        RuleAlias(EOF),
        Optional(RuleAlias(EndOfLine)),
        RuleAlias(EOF),
        Optional(RuleAlias(EOF)),
    ])
    chain.validate_sequence(token_sequence([EOF(None), EOF(None)]))
    chain.validate_sequence(token_sequence([EOF(None), EndOfLine(None), EOF(None)]))
    chain.validate_sequence(token_sequence([EOF(None), EndOfLine(None), EOF(None), EOF(None)]))
    chain.validate_sequence(token_sequence([EOF(None), EOF(None), EOF(None)]))
