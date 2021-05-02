from gherkin.compiler.rule import Chain, OneOf, Repeatable, Optional, RuleAlias
from gherkin.compiler.token import Language, Feature, EOF, Description, Rule, Scenario, EndOfLine, Tag, \
    Given, And, But, When, Then, Background


class AndButGrammar(object):
    rule = OneOf([
        Chain([
            RuleAlias(And),
            RuleAlias(Description),
            RuleAlias(EndOfLine),
        ]),
        Chain([
            RuleAlias(But),
            RuleAlias(Description),
            RuleAlias(EndOfLine),
        ]),
    ])


class GivenGrammar(object):
    rule = Chain([
        RuleAlias(Given),
        RuleAlias(Description),
        RuleAlias(EndOfLine),
        Repeatable(AndButGrammar.rule, minimum=0)
    ])


class WhenGrammar(object):
    rule = Chain([
        RuleAlias(When),
        RuleAlias(Description),
        RuleAlias(EndOfLine),
        Repeatable(AndButGrammar.rule, minimum=0)
    ])


class ThenGrammar(object):
    rule = Chain([
        RuleAlias(Then),
        RuleAlias(Description),
        RuleAlias(EndOfLine),
        Repeatable(AndButGrammar.rule, minimum=0)
    ])


class StepsGrammar(object):
    rule = Chain([
        Repeatable(GivenGrammar.rule, minimum=0),
        Repeatable(WhenGrammar.rule, minimum=0),
        Repeatable(ThenGrammar.rule, minimum=0),
    ])


class DescriptionGrammar(object):
    rule = Chain([
        RuleAlias(Description), RuleAlias(EndOfLine),
    ])


class TagGrammar(object):
    rule = Chain([
            Repeatable(RuleAlias(Tag), minimum=1),
            RuleAlias(EndOfLine),
        ])


class ScenarioGrammar(object):
    rule = Chain([
        Optional(TagGrammar.rule),
        RuleAlias(Scenario),
        OneOf([
            RuleAlias(EndOfLine),
            Repeatable(DescriptionGrammar.rule, minimum=0),
        ]),
        StepsGrammar.rule,
    ])


class RuleTokenGrammar(object):
    rule = Chain([
        Optional(TagGrammar.rule),
        RuleAlias(Rule),
        OneOf([
            RuleAlias(EndOfLine),
            Repeatable(DescriptionGrammar.rule, minimum=0),
        ]),
        Optional(Chain([
            RuleAlias(Background),
            RuleAlias(EndOfLine),
            StepsGrammar.rule,
        ])),
        Repeatable(ScenarioGrammar.rule, minimum=1)
    ])


class FeatureGrammar(object):
    rule = Chain([
        Optional(TagGrammar.rule),
        RuleAlias(Feature),
        OneOf([
            RuleAlias(EndOfLine),
            Repeatable(DescriptionGrammar.rule, minimum=0),
        ]),
        Optional(Chain([
            RuleAlias(Background),
            RuleAlias(EndOfLine),
            StepsGrammar.rule,
        ])),
        OneOf([
            Repeatable(RuleTokenGrammar.rule, minimum=1),
            Repeatable(ScenarioGrammar.rule, minimum=1),
        ]),
    ])


class GherkinDocumentGrammar(object):
    rule = Chain([
        Optional(Chain([
            RuleAlias(Language),
            RuleAlias(EndOfLine),
        ])),
        FeatureGrammar.rule,
        RuleAlias(EOF),
    ])
