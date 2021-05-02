from gherkin.compiler.rule import Chain, OneOf, Repeatable, Optional, RuleAlias
from gherkin.compiler.token import Language, Feature, EOF, Description, Rule, Scenario, EndOfLine, Tag, \
    Given, And, But, When, Then, Background, DocString, DataTable, Examples, ScenarioOutline


class DescriptionGrammar(object):
    rule = Chain([
        RuleAlias(Description), RuleAlias(EndOfLine),
    ])


class DocStringGrammar(object):
    rule = Chain([
        RuleAlias(DocString),
        RuleAlias(EndOfLine),
        Repeatable(DescriptionGrammar.rule, minimum=0),
        RuleAlias(DocString),
        RuleAlias(EndOfLine),
    ])


class DataTableGrammar(object):
    rule = Chain([
        Repeatable(Chain([
            RuleAlias(DataTable),
            RuleAlias(EndOfLine),
        ]), minimum=2),
    ])


class AndButGrammar(object):
    rule = OneOf([
        Chain([
            RuleAlias(And),
            RuleAlias(Description),
            RuleAlias(EndOfLine),
            Optional(OneOf([
                DocStringGrammar.rule,
                DataTableGrammar.rule,
            ])),
        ]),
        Chain([
            RuleAlias(But),
            RuleAlias(Description),
            RuleAlias(EndOfLine),
            Optional(OneOf([
                DocStringGrammar.rule,
                DataTableGrammar.rule,
            ])),
        ]),
    ])


class ExamplesGrammar(object):
    rule = Chain([
        RuleAlias(Examples),
        RuleAlias(EndOfLine),
        DataTableGrammar.rule,
    ])


class GivenGrammar(object):
    rule = Chain([
        RuleAlias(Given),
        RuleAlias(Description),
        RuleAlias(EndOfLine),
        Optional(OneOf([
            DocStringGrammar.rule,
            DataTableGrammar.rule,
        ])),
        Repeatable(AndButGrammar.rule, minimum=0),
    ])


class WhenGrammar(object):
    rule = Chain([
        RuleAlias(When),
        RuleAlias(Description),
        RuleAlias(EndOfLine),
        Optional(OneOf([
            DocStringGrammar.rule,
            DataTableGrammar.rule,
        ])),
        Repeatable(AndButGrammar.rule, minimum=0),
    ])


class ThenGrammar(object):
    rule = Chain([
        RuleAlias(Then),
        RuleAlias(Description),
        RuleAlias(EndOfLine),
        Optional(OneOf([
            DocStringGrammar.rule,
            DataTableGrammar.rule,
        ])),
        Repeatable(AndButGrammar.rule, minimum=0),
    ])


class StepsGrammar(object):
    rule = Chain([
        Repeatable(GivenGrammar.rule, minimum=0),
        Repeatable(WhenGrammar.rule, minimum=0),
        Repeatable(ThenGrammar.rule, minimum=0),
    ])


class TagGrammar(object):
    rule = Chain([
        Repeatable(RuleAlias(Tag)),
        RuleAlias(EndOfLine),
    ])


class ScenarioOutlineGrammar(object):
    rule = Chain([
        Optional(TagGrammar.rule),
        RuleAlias(ScenarioOutline),
        OneOf([
            RuleAlias(EndOfLine),
            Repeatable(DescriptionGrammar.rule, minimum=0),
        ]),
        StepsGrammar.rule,
        ExamplesGrammar.rule,
    ], debug=True)


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
        Repeatable(OneOf([
            ScenarioGrammar.rule,
            ScenarioOutlineGrammar.rule,
        ]))
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
            Repeatable(OneOf([
                ScenarioGrammar.rule,
                ScenarioOutlineGrammar.rule,
            ]), minimum=1),
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
