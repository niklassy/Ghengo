from gherkin.compiler.base.rule import Chain, OneOf, Repeatable, Optional, RuleAlias, Grammar, RuleToken
from gherkin.compiler.token import Language, Feature, EOF, Description, Rule, Scenario, EndOfLine, Tag, \
    Given, And, But, When, Then, Background, DocString, DataTable, Examples, ScenarioOutline
from gherkin.ast import GherkinDocument as ASTGherkinDocument, Language as ASTLanguage, \
    Feature as ASTFeature, Description as ASTDescription, Tag as ASTTag, Background as ASTBackground, \
    DocString as ASTDocString, DataTable as ASTDataTable, TableCell as ASTTableCell, TableRow as ASTTableRow, \
    And as ASTAnd, But as ASTBut, When as ASTWhen, Given as ASTGiven, Then as ASTThen, \
    ScenarioOutline as ASTScenarioOutline, Rule as ASTRule, Scenario as ASTScenario, Examples as ASTExamples
from settings import Settings


def get_name_and_description(descriptions):
    if isinstance(descriptions, list):
        name = descriptions[0].text

        if len(descriptions) > 1:
            description = ' '.join(d.text for d in descriptions[1:])
        else:
            description = None
    else:
        name = None
        description = None

    return name, description


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


class AndButGrammarBase(Grammar):
    def get_rule(self):
        return Chain([
            self.criterion_rule_alias,
            RuleAlias(Description),
            RuleAlias(EndOfLine),
            Optional(OneOf([
                DocStringGrammar(),
                DataTableGrammar(),
            ])),
        ])


class AndGrammar(AndButGrammarBase):
    criterion_rule_alias = RuleAlias(And)
    ast_object_cls = ASTAnd

    def get_ast_objects_kwargs(self, rule_output):
        return {
            'text': rule_output[1].token.text,
            'keyword': rule_output[0].token.matched_keyword,
        }


class ButGrammar(AndButGrammarBase):
    criterion_rule_alias = RuleAlias(But)
    ast_object_cls = ASTBut

    def get_ast_objects_kwargs(self, rule_output):
        return {
            'text': rule_output[1].token.text,
            'keyword': rule_output[0].token.matched_keyword,
        }


class TagsGrammarMixin(object):
    def prepare_object(self, rule_output, obj):
        obj = super().prepare_object(rule_output, obj)

        tags = rule_output[0]
        if tags and isinstance(tags, list):
            for tag in tags:
                obj.add_tag(tag)

        return obj


class ExamplesGrammar(TagsGrammarMixin, Grammar):
    criterion_rule_alias = RuleAlias(Examples)
    rule = Chain([
        Optional(TagsGrammar()),
        criterion_rule_alias,
        OneOf([
            RuleAlias(EndOfLine),
            Repeatable(DescriptionGrammar()),
        ]),
        DataTableGrammar(),
    ])
    ast_object_cls = ASTExamples

    def get_ast_objects_kwargs(self, rule_output):
        name, description = get_name_and_description(rule_output[2])

        return {
            'keyword': rule_output[1].token.matched_keyword,
            'name': name,
            'description': description,
            'datatable': rule_output[3]
        }


class GivenWhenThenBase(Grammar):
    def get_ast_objects_kwargs(self, rule_output):
        return {
            'keyword': rule_output[0].token.matched_keyword,
            'text': rule_output[1].token.text,
            'argument': rule_output[3]
        }

    def prepare_object(self, rule_output, obj):
        # add sub steps like BUT and AND
        sub_steps = rule_output[4]
        for step in sub_steps:
            obj.add_sub_step(step)

        return obj


class GivenGrammar(GivenWhenThenBase):
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
    ast_object_cls = ASTGiven


class WhenGrammar(GivenWhenThenBase):
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
    ast_object_cls = ASTWhen


class ThenGrammar(GivenWhenThenBase):
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
    ast_object_cls = ASTThen


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

    def sequence_to_object(self, sequence, index=0):
        output = []

        for step_list in self.get_rule_tree(sequence, index):
            for step in step_list:
                output.append(step)

        return output


class ScenarioDefinitionGrammar(Grammar):
    description_index = 2
    steps_index = 3

    def get_ast_objects_kwargs(self, rule_output):
        name, description = get_name_and_description(rule_output[self.description_index])

        return {
            'description': description,
            'keyword': rule_output[1].token.matched_keyword,
            'name': name,
        }

    def prepare_object(self, rule_output, obj):
        steps = rule_output[self.steps_index]

        # add each step to the definition
        for step in steps:
            obj.add_step(step)

        return obj


class ScenarioOutlineGrammar(TagsGrammarMixin, ScenarioDefinitionGrammar):
    criterion_rule_alias = RuleAlias(ScenarioOutline)
    rule = Chain([
        Optional(TagsGrammar()),
        criterion_rule_alias,
        OneOf([
            RuleAlias(EndOfLine),
            Repeatable(DescriptionGrammar()),
        ]),
        StepsGrammar(),
        Repeatable(ExamplesGrammar()),
    ])
    ast_object_cls = ASTScenarioOutline

    def prepare_object(self, rule_output, obj):
        """In addition to the steps, we need to add the argument of the Examples here."""
        obj = super().prepare_object(rule_output, obj)
        examples = rule_output[4]

        for example in examples:
            example.parent = obj
            obj.add_example(example)

        return obj


class ScenarioGrammar(TagsGrammarMixin, ScenarioDefinitionGrammar):
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
    ast_object_cls = ASTScenario


class BackgroundGrammar(ScenarioDefinitionGrammar):
    description_index = 1
    steps_index = 2
    criterion_rule_alias = RuleAlias(Background)
    rule = Chain([
        criterion_rule_alias,
        OneOf([
            RuleAlias(EndOfLine),
            Repeatable(DescriptionGrammar()),
        ]),
        Repeatable(GivenGrammar(), minimum=1),
    ])
    ast_object_cls = ASTBackground


class RuleTokenGrammar(TagsGrammarMixin, Grammar):
    criterion_rule_alias = RuleAlias(Rule)
    rule = Chain([
        Optional(TagsGrammar()),    # support was added some time ago (https://github.com/cucumber/common/pull/1356)
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
    ast_object_cls = ASTRule

    def get_ast_objects_kwargs(self, rule_output):
        name, description = get_name_and_description(rule_output[2])

        return {
            'description': description,
            'keyword': rule_output[1].token.matched_keyword,
            'name': name,
            'background': rule_output[3],
        }

    def prepare_object(self, rule_output, obj):
        # set tags
        obj = super().prepare_object(rule_output, obj)

        # set all the children/ scenario definitions
        for sr in rule_output[4]:
            sr.parent = obj
            obj.add_child(sr)

        return obj


class FeatureGrammar(TagsGrammarMixin, Grammar):
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

    def get_ast_objects_kwargs(self, rule_output):
        name, description = get_name_and_description(rule_output[2])

        return {
            'description': description,
            'keyword': rule_output[1].token.matched_keyword,
            'name': name,
            'language': Settings.language,
            'background': rule_output[3],
        }

    def prepare_object(self, rule_output: [RuleToken], obj: ASTFeature):
        scenario_rules = rule_output[4]

        # add all the rules/ scenario definitions
        for sr in scenario_rules:
            sr.parent = obj
            obj.add_child(sr)

        return obj


class LanguageGrammar(Grammar):
    criterion_rule_alias = RuleAlias(Language)
    rule = Chain([
        criterion_rule_alias,
        RuleAlias(EndOfLine),
    ])
    ast_object_cls = ASTLanguage

    def get_ast_objects_kwargs(self, rule_output):
        return {'language': rule_output[0].token.locale}


class GherkinDocumentGrammar(Grammar):
    rule = Chain([
        Optional(LanguageGrammar()),
        Optional(FeatureGrammar()),
        RuleAlias(EOF),
    ])
    criterion_rule_alias = None
    name = 'Gherkin document'
    ast_object_cls = ASTGherkinDocument

    def prepare_object(self, rule_output, obj):
        feature = rule_output[1]

        # set the feature if it exists
        if feature:
            obj.set_feature(feature)

        return obj
