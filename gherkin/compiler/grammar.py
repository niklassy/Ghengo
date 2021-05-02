from gherkin.compiler.rule import Chain, OneOf, Repeatable, Optional, RuleClass
from gherkin.compiler.token import Language, Feature, EOF, Description, Rule, Scenario, EndOfLine, Tag, \
    Given, And, But, When, Then, Background


class AndButGrammar(object):
    rule = OneOf([
        Chain([
            RuleClass(And),
            RuleClass(Description),
            RuleClass(EndOfLine),
        ]),
        Chain([
            RuleClass(But),
            RuleClass(Description),
            RuleClass(EndOfLine),
        ]),
    ])


class GivenGrammar(object):
    rule = Chain([
        RuleClass(Given),
        RuleClass(Description),
        RuleClass(EndOfLine),
        Repeatable(AndButGrammar.rule, minimum=0)
    ])


class WhenGrammar(object):
    rule = Chain([
        RuleClass(When),
        RuleClass(Description),
        RuleClass(EndOfLine),
        Repeatable(AndButGrammar.rule, minimum=0)
    ])


class ThenGrammar(object):
    rule = Chain([
        RuleClass(Then),
        RuleClass(Description),
        RuleClass(EndOfLine),
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
        RuleClass(Description), RuleClass(EndOfLine),
    ])


class ScenarioGrammar(object):
    rule = Chain([
        Optional(Chain([
            Repeatable(RuleClass(Tag), minimum=1),
            RuleClass(EndOfLine),
        ])),
        RuleClass(Scenario),
        OneOf([
            RuleClass(EndOfLine),
            Repeatable(DescriptionGrammar.rule, minimum=0),
        ]),
        StepsGrammar.rule,
    ])


class RuleTokenGrammar(object):
    rule = Chain([
        Optional(Chain([
            Repeatable(RuleClass(Tag), minimum=1),
            RuleClass(EndOfLine),
        ])),
        RuleClass(Rule),
        OneOf([
            RuleClass(EndOfLine),
            Repeatable(DescriptionGrammar.rule, minimum=0),
        ]),
        Optional(Chain([
            RuleClass(Background),
            RuleClass(EndOfLine),
            StepsGrammar.rule,
        ])),
        Repeatable(ScenarioGrammar.rule, minimum=1)
    ])


class FeatureGrammar(object):
    rule = Chain([
        Optional(Chain([
            Repeatable(RuleClass(Tag), minimum=1),
            RuleClass(EndOfLine),
        ])),
        RuleClass(Feature),
        OneOf([
            RuleClass(EndOfLine),
            Repeatable(DescriptionGrammar.rule, minimum=0),
        ]),
        Optional(Chain([
            RuleClass(Background),
            RuleClass(EndOfLine),
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
            RuleClass(Language),
            RuleClass(EndOfLine),
        ])),
        FeatureGrammar.rule,
        RuleClass(EOF),
    ])
