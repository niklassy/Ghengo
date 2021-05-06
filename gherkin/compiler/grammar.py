from gherkin.compiler.rule import Chain, OneOf, Repeatable, Optional, RuleAlias, Grammar, RuleToken
from gherkin.compiler.token import Language, Feature, EOF, Description, Rule, Scenario, EndOfLine, Tag, \
    Given, And, But, When, Then, Background, DocString, DataTable, Examples, ScenarioOutline
from gherkin.compiler.ast import GherkinDocument as ASTGherkinDocument, Language as ASTLanguage, \
    Feature as ASTFeature, Description as ASTDescription, Tag as ASTTag
from settings import Settings


class DescriptionGrammar(Grammar):
    criterion_rule_alias = RuleAlias(Description)
    rule = Chain([
        criterion_rule_alias,
        RuleAlias(EndOfLine),
    ])
    ast_object_cls = ASTDescription

    def get_ast_objects_kwargs(self, rule_output):
        return {
            'text': rule_output[0].token.text,
        }


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


class TagsGrammar(Grammar):
    criterion_rule_alias = RuleAlias(Tag)
    rule = Chain([
        Repeatable(criterion_rule_alias),
        RuleAlias(EndOfLine),
    ])
    ast_object_cls = ASTTag

    def convert_to_object(self, sequence, index=0):
        tags = []
        rule_tree = self.get_rule_tree(sequence, index)

        for tag in rule_tree[0]:
            tags.append(ASTTag(tag.token.text))

        return tags


class ScenarioOutlineGrammar(Grammar):
    criterion_rule_alias = RuleAlias(ScenarioOutline)
    rule = Chain([
        Optional(TagsGrammar()),
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
        Optional(TagsGrammar()),
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
    criterion_rule_alias = RuleAlias(Feature)
    rule = Chain([
        Optional(TagsGrammar()),
        criterion_rule_alias,
        OneOf([
            RuleAlias(EndOfLine),
            Repeatable(DescriptionGrammar()),
        ]),
        Optional(Chain([
            # TODO: Background grammar!
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
    ast_object_cls = ASTFeature

    def prepare_object(self, rule_tree: [RuleToken], obj: ASTFeature):
        obj.language = Settings.language

        tags = rule_tree[0]
        if tags and isinstance(tags, list):
            for t in tags:
                obj.add_tag(t)

        # handle feature
        obj.keyword = rule_tree[1].token.matched_keyword

        # handle description
        if isinstance(rule_tree[2], list):
            descriptions = rule_tree[2]
            obj.name = descriptions[0].text

            if len(descriptions) > 1:
                obj.description = ' '.join([d.text for d in descriptions[1:]])

        # TODO: handle scenario definitions

        return obj


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
    ast_object_cls = ASTGherkinDocument

    def prepare_object(self, rule_tree, obj):
        feature = rule_tree[1]

        if feature:
            obj.set_feature(feature)

        return obj
