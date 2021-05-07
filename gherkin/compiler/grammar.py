from gherkin.compiler.rule import Chain, OneOf, Repeatable, Optional, RuleAlias, Grammar, RuleToken
from gherkin.compiler.token import Language, Feature, EOF, Description, Rule, Scenario, EndOfLine, Tag, \
    Given, And, But, When, Then, Background, DocString, DataTable, Examples, ScenarioOutline
from gherkin.compiler.ast import GherkinDocument as ASTGherkinDocument, Language as ASTLanguage, \
    Feature as ASTFeature, Description as ASTDescription, Tag as ASTTag, Background as ASTBackground, \
    DocString as ASTDocString, DataTable as ASTDataTable, TableCell as ASTTableCell, TableRow as ASTTableRow, \
    And as ASTAnd, But as ASTBut, When as ASTWhen, Given as ASTGiven, Then as ASTThen
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
    ast_object_cls = ASTDocString

    def get_ast_objects_kwargs(self, rule_output):
        descriptions = rule_output[2]

        if len(descriptions) > 0:
            text = ' '.join([d.text for d in descriptions])
        else:
            text = ''

        return {'text': text}


class DataTableGrammar(Grammar):
    criterion_rule_alias = RuleAlias(DataTable)
    rule = Chain([
        Repeatable(Chain([
            criterion_rule_alias,
            RuleAlias(EndOfLine),
        ]), minimum=2),
    ])
    ast_object_cls = ASTDataTable

    @classmethod
    def get_values_of_datatable(cls, entry):
        header_entry = entry[0]     # <- second entry is always the end of line, so take the first
        return [v.lstrip().rstrip() for v in header_entry.token.text.split('|') if v.lstrip().rstrip()]

    def get_ast_objects_kwargs(self, rule_output):
        datatable_entries = rule_output[0]
        header_row = datatable_entries[0]
        header_values = self.get_values_of_datatable(header_row)
        header = ASTTableRow(cells=[ASTTableCell(value=v) for v in header_values])

        rows = []
        for row in datatable_entries[1:]:
            row_values = self.get_values_of_datatable(row)
            rows.append(ASTTableRow(cells=[ASTTableCell(value=v) for v in row_values]))

        return {
            'header': header,
            'rows': rows,
        }


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
    ast_object_cls = ASTAnd

    def get_ast_objects_kwargs(self, rule_output):
        return {
            'text': rule_output[1].token.text,
            'keyword': rule_output[0].token.matched_keyword,
        }


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


class StepsGrammar(Grammar):
    rule = Chain([
        Repeatable(GivenGrammar(), minimum=0),
        Repeatable(WhenGrammar(), minimum=0),
        Repeatable(ThenGrammar(), minimum=0),
    ])
    name = 'Steps'

    def used_by_sequence_area(self, sequence, start_index, end_index):
        given = GivenGrammar().used_by_sequence_area(sequence, start_index, end_index)
        when = WhenGrammar().used_by_sequence_area(sequence, start_index, end_index)
        then = ThenGrammar().used_by_sequence_area(sequence, start_index, end_index)

        return given or when or then


class TagsGrammar(Grammar):
    criterion_rule_alias = RuleAlias(Tag)
    rule = Chain([
        Repeatable(criterion_rule_alias),
        RuleAlias(EndOfLine),
    ])
    ast_object_cls = ASTTag

    def sequence_to_object(self, sequence, index=0):
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
        StepsGrammar(),
        ExamplesGrammar(),
    ])

    def prepare_object(self, rule_tree, obj):
        # TODO: add examples content to arguments
        return obj


class ScenarioGrammar(Grammar):
    criterion_rule_alias = RuleAlias(Scenario)
    rule = Chain([
        Optional(TagsGrammar()),
        criterion_rule_alias,
        OneOf([
            RuleAlias(EndOfLine),
            Repeatable(DescriptionGrammar()),
        ]),
        StepsGrammar(),
    ])


class BackgroundGrammar(Grammar):
    criterion_rule_alias = RuleAlias(Background)
    rule = Chain([
        RuleAlias(Background),
        OneOf([
            RuleAlias(EndOfLine),
            Repeatable(DescriptionGrammar()),
        ]),
        Repeatable(GivenGrammar(), minimum=1),
    ])
    ast_object_cls = ASTBackground

    def get_ast_objects_kwargs(self, rule_output):
        output = {
            'keyword': rule_output[0].token.matched_keyword,
        }

        if isinstance(rule_output[1], list):
            descriptions = rule_output[1]
            output['name'] = descriptions[0].text

            if len(descriptions) > 1:
                output['description'] = ' '.join([d.text for d in descriptions[1:]])
        else:
            output['name'] = None
            output['description'] = None

        return output

    def prepare_object(self, rule_tree, obj):
        # TODO: add steps
        pass


class RuleTokenGrammar(Grammar):
    criterion_rule_alias = RuleAlias(Rule)
    rule = Chain([
        criterion_rule_alias,
        OneOf([
            RuleAlias(EndOfLine),
            Repeatable(DescriptionGrammar()),
        ]),
        Optional(BackgroundGrammar()),
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
        Optional(BackgroundGrammar()),
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
        # language was already set previously
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

        # set the feature if it exists
        if feature:
            obj.set_feature(feature)

        return obj
