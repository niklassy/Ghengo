from gherkin.compiler.rule import Chain, OneOf, Repeatable, Optional, RuleAlias, Grammar, RuleToken
from gherkin.compiler.token import Language, Feature, EOF, Description, Rule, Scenario, EndOfLine, Tag, \
    Given, And, But, When, Then, Background, DocString, DataTable, Examples, ScenarioOutline
from gherkin.compiler.ast import GherkinDocument as ASTGherkinDocument, Language as ASTLanguage


class DescriptionGrammar(Grammar):
    criterion_rule_alias = RuleAlias(Description)
    rule = Chain([
        criterion_rule_alias,
        RuleAlias(EndOfLine),
    ])


class DocStringGrammar(Grammar):
    criterion_rule_alias = RuleAlias(DocString)
    rule = Chain([
        criterion_rule_alias,
        RuleAlias(EndOfLine),
        Repeatable(DescriptionGrammar(), minimum=0),
        RuleAlias(DocString),
        RuleAlias(EndOfLine),
    ])


class DataTableGrammar(Grammar):
    criterion_rule_alias = RuleAlias(DataTable)
    rule = Chain([
        Repeatable(Chain([
            criterion_rule_alias,
            RuleAlias(EndOfLine),
        ]), minimum=2),
    ])


class AndGrammar(Grammar):
    criterion_rule_alias = RuleAlias(And)
    rule = Chain([
        criterion_rule_alias,
        RuleAlias(Description),
        RuleAlias(EndOfLine),
        Optional(OneOf([
            DocStringGrammar(),
            DataTableGrammar(),
        ])),
    ])


class ButGrammar(Grammar):
    criterion_rule_alias = RuleAlias(But)
    rule = Chain([
        criterion_rule_alias,
        RuleAlias(Description),
        RuleAlias(EndOfLine),
        Optional(OneOf([
            DocStringGrammar(),
            DataTableGrammar(),
        ])),
    ])


class ExamplesGrammar(Grammar):
    criterion_rule_alias = RuleAlias(Examples)
    rule = Chain([
        criterion_rule_alias,
        RuleAlias(EndOfLine),
        DataTableGrammar(),
    ])


class GivenGrammar(Grammar):
    criterion_rule_alias = RuleAlias(Given)
    rule = Chain([
        criterion_rule_alias,
        RuleAlias(Description),
        RuleAlias(EndOfLine),
        Optional(OneOf([
            DocStringGrammar(),
            DataTableGrammar(),
        ])),
        Repeatable(OneOf([AndGrammar(), ButGrammar()]), minimum=0),
    ])


class WhenGrammar(Grammar):
    criterion_rule_alias = RuleAlias(When)
    rule = Chain([
        criterion_rule_alias,
        RuleAlias(Description),
        RuleAlias(EndOfLine),
        Optional(OneOf([
            DocStringGrammar(),
            DataTableGrammar(),
        ])),
        Repeatable(OneOf([AndGrammar(), ButGrammar()]), minimum=0),
    ])


class ThenGrammar(Grammar):
    criterion_rule_alias = RuleAlias(Then)
    rule = Chain([
        criterion_rule_alias,
        RuleAlias(Description),
        RuleAlias(EndOfLine),
        Optional(OneOf([
            DocStringGrammar(),
            DataTableGrammar(),
        ])),
        Repeatable(OneOf([AndGrammar(), ButGrammar()]), minimum=0),
    ])


StepsGrammar = Chain([
    Repeatable(GivenGrammar(), minimum=0),
    Repeatable(WhenGrammar(), minimum=0),
    Repeatable(ThenGrammar(), minimum=0),
])


class TagGrammar(Grammar):
    criterion_rule_alias = RuleAlias(Tag)
    rule = Chain([
        Repeatable(criterion_rule_alias),
        RuleAlias(EndOfLine),
    ])


class ScenarioOutlineGrammar(Grammar):
    criterion_rule_alias = RuleAlias(ScenarioOutline)
    rule = Chain([
        Optional(TagGrammar()),
        criterion_rule_alias,
        OneOf([
            RuleAlias(EndOfLine),
            Repeatable(DescriptionGrammar()),
        ]),
        StepsGrammar,
        ExamplesGrammar(),
    ])


class ScenarioGrammar(Grammar):
    criterion_rule_alias = RuleAlias(Scenario)
    rule = Chain([
        Optional(TagGrammar()),
        criterion_rule_alias,
        OneOf([
            RuleAlias(EndOfLine),
            Repeatable(DescriptionGrammar()),
        ]),
        StepsGrammar,
    ])


class RuleTokenGrammar(Grammar):
    criterion_rule_alias = RuleAlias(Rule)
    rule = Chain([
        criterion_rule_alias,
        OneOf([
            RuleAlias(EndOfLine),
            Repeatable(DescriptionGrammar()),
        ]),
        Optional(Chain([
            RuleAlias(Background),
            RuleAlias(EndOfLine),
            StepsGrammar,
        ])),
        Repeatable(OneOf([
            ScenarioGrammar(),
            ScenarioOutlineGrammar(),
        ]))
    ])


class FeatureGrammar(Grammar):
    class FeaturePlaceholder(object):
        pass

    criterion_rule_alias = RuleAlias(Feature)
    rule = Chain([
        Optional(TagGrammar()),
        criterion_rule_alias,
        OneOf([
            RuleAlias(EndOfLine),
            Repeatable(DescriptionGrammar()),
        ]),
        Optional(Chain([
            RuleAlias(Background),
            RuleAlias(EndOfLine),
            StepsGrammar,
        ])),
        OneOf([
            Repeatable(RuleTokenGrammar()),
            Repeatable(OneOf([
                ScenarioGrammar(),
                ScenarioOutlineGrammar(),
            ])),
        ]),
    ])
    ast_object_cls = FeaturePlaceholder


class LanguageGrammar(Grammar):
    criterion_rule_alias = RuleAlias(Language)
    rule = Chain([
        criterion_rule_alias,
        RuleAlias(EndOfLine),
    ])
    ast_object_cls = ASTLanguage


class GherkinDocumentGrammar(Grammar):
    rule = Chain([
        Optional(LanguageGrammar()),
        Optional(FeatureGrammar()),
        RuleAlias(EOF),
    ])
    criterion_rule_alias = None
    name = 'Gherkin document'

    def convert_to_object(self, sequence, index=0):
        output = super().convert_to_object(sequence, index)
        doc = ASTGherkinDocument()

        # check if there is a feature; if yes, add it
        if output[1]:
            doc.set_feature(output[0])

        return doc
