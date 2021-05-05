from gherkin.compiler.rule import Optional, RuleAlias, RuleToken, Grammar, Chain, GrammarInvalid, RuleNotFulfilled, \
    SequenceNotFinished, OneOf, Repeatable
from gherkin.compiler.token import Description, EndOfLine, EOF, Feature
from test_utils import assert_callable_raises


class RuleTestToken(RuleToken):
    def get_place_to_search(self) -> str:
        return ''


def token_sequence(sequence):
    return [RuleTestToken(t) for t in sequence]


def test_optional_invalid_input():
    """Check if invalid input to optional is handled."""
    assert_callable_raises(Optional, ValueError, args=(Description,))
    assert_callable_raises(Optional, ValueError, args=([RuleAlias(Description)],))
    assert_callable_raises(Optional, ValueError, args=(Repeatable(RuleAlias(EOF)),))


def test_optional_rule_alias():
    """Check that an optional rule makes everything related to a rule alias pass."""
    # ======= validate a rule alias
    optional = Optional(RuleAlias(Description))
    optional.validate_sequence(token_sequence([Description('', None)]))
    optional.validate_sequence([])


def test_optional_grammar():
    """Check that an optional makes grammars pass if they are not used."""
    class TestGrammar(Grammar):
        criterion_rule_alias = RuleAlias(Description)
        rule = Chain([criterion_rule_alias, RuleAlias(EndOfLine)])

    optional = Optional(TestGrammar())
    # the grammar is used, so the grammar should raise an error and Optional should not catch it
    assert_callable_raises(
        optional.validate_sequence,
        GrammarInvalid,
        args=(token_sequence([Description('', None), Description('', None)]),),
    )

    optional.validate_sequence(token_sequence([]))


def test_optional_chain():
    """Check that optional behaves as expected when combined with a Chain."""
    optional = Optional(Chain([
        RuleAlias(Description),
        RuleAlias(EndOfLine),
    ]))
    optional.validate_sequence(token_sequence([]))
    optional.validate_sequence(token_sequence([Description('', None), EndOfLine(None)]))

    assert_callable_raises(
        optional.validate_sequence,
        SequenceNotFinished,
        args=(token_sequence([EOF(None)]),)
    )


def test_optional_one_of():
    """Check that one of is correctly handled by Optional."""
    optional = Chain([
        Optional(OneOf([
            RuleAlias(Description),
            RuleAlias(EndOfLine),
        ])),
        RuleAlias(EOF),
    ])
    optional.validate_sequence(token_sequence([EOF(None)]))
    optional.validate_sequence(token_sequence([Description('', None), EOF(None)]))
    optional.validate_sequence(token_sequence([EndOfLine(None), EOF(None)]))

    assert_callable_raises(
        optional.validate_sequence,
        RuleNotFulfilled,
        args=(token_sequence([Feature('', None), EOF(None)]),),
    )

