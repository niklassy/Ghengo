from gherkin.compiler_base.exception import GrammarInvalid
from gherkin.compiler_base.rule import Chain, OneOf, Repeatable, Optional, RuleAlias, Grammar, TokenWrapper
from gherkin.token import LanguageToken, FeatureToken, EOFToken, DescriptionToken, RuleToken, ScenarioToken, \
    EndOfLineToken, TagToken, GivenToken, AndToken, ButToken, WhenToken, ThenToken, BackgroundToken, \
    DocStringToken, DataTableToken, ExamplesToken, ScenarioOutlineToken
from gherkin.ast import GherkinDocument, Language, \
    Feature, Description, Tag, Background, \
    DocString, DataTable, TableCell, TableRow, \
    And, But, When, Given, Then, \
    ScenarioOutline, Rule, Scenario, Examples
from settings import Settings


class DescriptionGrammar(Grammar):
    criterion_rule_alias = RuleAlias(DescriptionToken)
    rule = Chain([
        criterion_rule_alias,
        RuleAlias(EndOfLineToken),
    ])
    convert_cls = Description

    def get_convert_kwargs(self, rule_output):
        return {
            'text': rule_output[0].token.text,
        }

    @staticmethod
    def get_name_and_description(descriptions_input):
        """
        Since descriptions are used in several places to define the name and description of Grammars, this function
        can be used to determine the name and the description from a list of ASTDescription objects.

        The input can be in the format:
        [Description]
        OR
        [EndOfLineTokenWrapper, [Description]]
        """
        if not isinstance(descriptions_input, list):
            return None, None

        # if the second entry in the list is a list, it holds all the descriptions
        if len(descriptions_input) > 1 and isinstance(descriptions_input[1], list):
            name = None
            descriptions = descriptions_input[1]
        # if a list of descriptions is passed instead, the first entry holds the name and the
        # rest the descriptions
        else:
            name = descriptions_input[0].text
            descriptions = descriptions_input[1:]

        if len(descriptions) > 0:
            return name, ' '.join(d.text for d in descriptions)

        return name, None


class TagsGrammar(Grammar):
    criterion_rule_alias = RuleAlias(TagToken)
    rule = Chain([
        Repeatable(criterion_rule_alias),
        RuleAlias(EndOfLineToken),
    ])
    convert_cls = Tag

    def sequence_to_object(self, sequence, index=0):
        tags = []
        rule_tree = self.get_rule_sequence_to_object(sequence, index)

        for tag in rule_tree[0]:
            tags.append(self.convert_cls(tag.token.text_without_keyword))

        return tags


class DocStringGrammar(Grammar):
    criterion_rule_alias = RuleAlias(DocStringToken)
    rule = Chain([
        criterion_rule_alias,
        RuleAlias(EndOfLineToken),
        Repeatable(DescriptionGrammar(), minimum=0),
        criterion_rule_alias,
        RuleAlias(EndOfLineToken),
    ])
    convert_cls = DocString

    def get_convert_kwargs(self, rule_output):
        descriptions = rule_output[2]

        if len(descriptions) > 0:
            text = ' '.join([d.text for d in descriptions])
        else:
            text = ''

        return {'text': text}


class DataTableGrammar(Grammar):
    criterion_rule_alias = RuleAlias(DataTableToken)
    rule = Chain([
        Repeatable(Chain([
            criterion_rule_alias,
            RuleAlias(EndOfLineToken),
        ]), minimum=2),
    ])
    convert_cls = DataTable

    def _validate_sequence(self, sequence, index):
        old_index = index
        new_index = super()._validate_sequence(sequence, index)
        nmb_columns = None

        # for through each token that belongs to the data table
        for token_wrapper in sequence[old_index:new_index]:
            # get the token
            data_table_token = token_wrapper.token

            # skip if EndOfLine
            if not isinstance(data_table_token, DataTableToken):
                continue

            # get all columns of that token
            token_columns = self.get_datatable_values(data_table_token.text)

            # first time, set the number of columns
            if nmb_columns is None:
                nmb_columns = len(token_columns)
                continue

            # for each of next data table entry, check that it has the same amount of columns
            if len(token_columns) != nmb_columns:
                place_to_search = token_wrapper.get_place_to_search()
                raise GrammarInvalid(
                    'All rows in a data table must have the same amount of columns. {}'.format(place_to_search),
                    grammar=self
                )

        return new_index

    @classmethod
    def get_datatable_values(cls, string):
        """Returns all the values inside of a given string."""
        return [v.lstrip().rstrip() for v in string.split('|') if v.lstrip().rstrip()]

    def get_convert_kwargs(self, rule_output):
        datatable_entries = rule_output[0]
        header_row = datatable_entries[0]
        header_values = self.get_datatable_values(header_row[0].token.text)     # <- header_row[1] will be EndOfLine
        header = TableRow(cells=[TableCell(value=v) for v in header_values])

        rows = []
        for row in datatable_entries[1:]:
            row_values = self.get_datatable_values(row[0].token.text)
            rows.append(TableRow(cells=[TableCell(value=v) for v in row_values]))

        return {
            'header': header,
            'rows': rows,
        }


class AndButGrammarBase(Grammar):
    def get_rule(self):
        return Chain([
            self.criterion_rule_alias,
            RuleAlias(DescriptionToken),
            RuleAlias(EndOfLineToken),
            Optional(OneOf([
                DocStringGrammar(),
                DataTableGrammar(),
            ])),
        ])

    def get_convert_kwargs(self, rule_output):
        return {
            'text': rule_output[1].token.text,
            'keyword': rule_output[0].token.matched_keyword,
            'argument': rule_output[3],
        }


class AndGrammar(AndButGrammarBase):
    criterion_rule_alias = RuleAlias(AndToken)
    convert_cls = And


class ButGrammar(AndButGrammarBase):
    criterion_rule_alias = RuleAlias(ButToken)
    convert_cls = But


class TagsGrammarMixin(object):
    def prepare_converted_object(self, rule_output, obj):
        obj = super().prepare_converted_object(rule_output, obj)

        tags = rule_output[0]
        if tags and isinstance(tags, list):
            for tag in tags:
                obj.add_tag(tag)

        return obj


class ExamplesGrammar(TagsGrammarMixin, Grammar):
    criterion_rule_alias = RuleAlias(ExamplesToken)
    rule = Chain([
        Optional(TagsGrammar()),
        criterion_rule_alias,
        OneOf([
            Chain([RuleAlias(EndOfLineToken), Repeatable(DescriptionGrammar(), minimum=0)]),
            Repeatable(DescriptionGrammar()),
        ]),
        DataTableGrammar(),
    ])
    convert_cls = Examples

    def get_convert_kwargs(self, rule_output):
        name, description = DescriptionGrammar.get_name_and_description(rule_output[2])

        return {
            'keyword': rule_output[1].token.matched_keyword,
            'name': name,
            'description': description,
            'datatable': rule_output[3]
        }


class GivenWhenThenBase(Grammar):
    def get_convert_kwargs(self, rule_output):
        return {
            'keyword': rule_output[0].token.matched_keyword,
            'text': rule_output[1].token.text,
            'argument': rule_output[3]
        }

    def prepare_converted_object(self, rule_convert_obj, grammar_obj):
        # add sub steps like BUT and AND
        sub_steps = rule_convert_obj[4]
        for step in sub_steps:
            grammar_obj.add_sub_step(step)

        return grammar_obj


class GivenGrammar(GivenWhenThenBase):
    criterion_rule_alias = RuleAlias(GivenToken)
    rule = Chain([
        criterion_rule_alias,
        RuleAlias(DescriptionToken),
        RuleAlias(EndOfLineToken),
        Optional(OneOf([
            DocStringGrammar(),
            DataTableGrammar(),
        ])),
        Repeatable(OneOf([AndGrammar(), ButGrammar()]), minimum=0),
    ])
    convert_cls = Given


class WhenGrammar(GivenWhenThenBase):
    criterion_rule_alias = RuleAlias(WhenToken)
    rule = Chain([
        criterion_rule_alias,
        RuleAlias(DescriptionToken),
        RuleAlias(EndOfLineToken),
        Optional(OneOf([
            DocStringGrammar(),
            DataTableGrammar(),
        ])),
        Repeatable(OneOf([AndGrammar(), ButGrammar()]), minimum=0),
    ])
    convert_cls = When


class ThenGrammar(GivenWhenThenBase):
    criterion_rule_alias = RuleAlias(ThenToken)
    rule = Chain([
        criterion_rule_alias,
        RuleAlias(DescriptionToken),
        RuleAlias(EndOfLineToken),
        Optional(OneOf([
            DocStringGrammar(),
            DataTableGrammar(),
        ])),
        Repeatable(OneOf([AndGrammar(), ButGrammar()]), minimum=0),
    ])
    convert_cls = Then


class StepsGrammar(Grammar):
    rule = Chain([
        Repeatable(GivenGrammar(), minimum=0),
        Repeatable(WhenGrammar(), minimum=0),
        Repeatable(ThenGrammar(), minimum=0),
    ])
    name = 'Steps'

    def _validate_sequence(self, sequence, index):
        new_index = super()._validate_sequence(sequence, index)

        # there has to be at least one step!
        if new_index == index:
            if index > len(sequence) - 1:
                token_wrapper = sequence[-1]
            else:
                token_wrapper = sequence[index]

            place_to_search = token_wrapper.get_place_to_search()
            raise GrammarInvalid(
                'You must use at least one Given, When or Then. {}'.format(place_to_search),
                grammar=self
            )

        return new_index

    def used_by_sequence_area(self, sequence, start_index, end_index):
        given = GivenGrammar().used_by_sequence_area(sequence, start_index, end_index)
        when = WhenGrammar().used_by_sequence_area(sequence, start_index, end_index)
        then = ThenGrammar().used_by_sequence_area(sequence, start_index, end_index)

        return given or when or then

    def sequence_to_object(self, sequence, index=0):
        output = []

        for step_list in self.get_rule_sequence_to_object(sequence, index):
            for step in step_list:
                output.append(step)

        return output


class ScenarioDefinitionGrammar(Grammar):
    description_index = 2
    steps_index = 3

    def get_convert_kwargs(self, rule_output):
        name, description = DescriptionGrammar.get_name_and_description(rule_output[self.description_index])

        return {
            'description': description,
            'keyword': rule_output[self.description_index - 1].token.matched_keyword,
            'name': name,
        }

    def prepare_converted_object(self, rule_convert_obj, grammar_obj):
        steps = rule_convert_obj[self.steps_index]

        # add each step to the definition
        for step in steps:
            grammar_obj.add_step(step)

        return grammar_obj


class ScenarioOutlineGrammar(TagsGrammarMixin, ScenarioDefinitionGrammar):
    criterion_rule_alias = RuleAlias(ScenarioOutlineToken)
    rule = Chain([
        Optional(TagsGrammar()),
        criterion_rule_alias,
        OneOf([
            Chain([RuleAlias(EndOfLineToken), Repeatable(DescriptionGrammar(), minimum=0)]),
            Repeatable(DescriptionGrammar()),
        ]),
        StepsGrammar(),
        Repeatable(ExamplesGrammar()),
    ])
    convert_cls = ScenarioOutline

    def prepare_converted_object(self, rule_convert_obj, grammar_obj: ScenarioOutline):
        """In addition to the steps, we need to add the argument of the Examples here."""
        grammar_obj = super().prepare_converted_object(rule_convert_obj, grammar_obj)
        examples = rule_convert_obj[4]

        for example in examples:
            example.parent = grammar_obj
            grammar_obj.add_example(example)

        return grammar_obj


class ScenarioGrammar(TagsGrammarMixin, ScenarioDefinitionGrammar):
    criterion_rule_alias = RuleAlias(ScenarioToken)
    rule = Chain([
        Optional(TagsGrammar()),
        criterion_rule_alias,
        OneOf([
            Chain([RuleAlias(EndOfLineToken), Repeatable(DescriptionGrammar(), minimum=0)]),
            Repeatable(DescriptionGrammar()),
        ]),
        StepsGrammar(),
    ])
    convert_cls = Scenario


class BackgroundGrammar(ScenarioDefinitionGrammar):
    description_index = 1
    steps_index = 2
    criterion_rule_alias = RuleAlias(BackgroundToken)
    rule = Chain([
        criterion_rule_alias,
        OneOf([
            Chain([RuleAlias(EndOfLineToken), Repeatable(DescriptionGrammar(), minimum=0)]),
            Repeatable(DescriptionGrammar()),
        ]),
        Repeatable(GivenGrammar(), minimum=1),
    ])
    convert_cls = Background


class RuleGrammar(TagsGrammarMixin, Grammar):
    criterion_rule_alias = RuleAlias(RuleToken)
    rule = Chain([
        Optional(TagsGrammar()),    # support was added some time ago (https://github.com/cucumber/common/pull/1356)
        criterion_rule_alias,
        OneOf([
            Chain([RuleAlias(EndOfLineToken), Repeatable(DescriptionGrammar(), minimum=0)]),
            Repeatable(DescriptionGrammar()),
        ]),
        Optional(BackgroundGrammar()),
        Repeatable(OneOf([
            ScenarioGrammar(),
            ScenarioOutlineGrammar(),
        ]))
    ])
    convert_cls = Rule

    def get_convert_kwargs(self, rule_output):
        name, description = DescriptionGrammar.get_name_and_description(rule_output[2])

        return {
            'description': description,
            'keyword': rule_output[1].token.matched_keyword,
            'name': name,
            'background': rule_output[3],
        }

    def prepare_converted_object(self, rule_convert_obj, grammar_obj: Rule):
        # set tags
        grammar_obj = super().prepare_converted_object(rule_convert_obj, grammar_obj)

        # set all the children/ scenario definitions
        for sr in rule_convert_obj[4]:
            sr.parent = grammar_obj
            grammar_obj.add_scenario_definition(sr)

        return grammar_obj


class FeatureGrammar(TagsGrammarMixin, Grammar):
    criterion_rule_alias = RuleAlias(FeatureToken)
    rule = Chain([
        Optional(TagsGrammar()),
        criterion_rule_alias,
        OneOf([
            Chain([RuleAlias(EndOfLineToken), Repeatable(DescriptionGrammar(), minimum=0)]),
            Repeatable(DescriptionGrammar()),
        ]),
        Optional(BackgroundGrammar()),
        OneOf([
            Repeatable(RuleGrammar()),
            Repeatable(OneOf([
                ScenarioGrammar(),
                ScenarioOutlineGrammar(),
            ])),
        ]),
    ])
    convert_cls = Feature

    def get_convert_kwargs(self, rule_output):
        name, description = DescriptionGrammar.get_name_and_description(rule_output[2])

        return {
            'description': description,
            'keyword': rule_output[1].token.matched_keyword,
            'name': name,
            'language': Settings.language,
            'background': rule_output[3],
        }

    def prepare_converted_object(self, rule_convert_obj: [TokenWrapper], grammar_obj: Feature):
        grammar_obj = super().prepare_converted_object(rule_convert_obj, grammar_obj)
        scenario_rules = rule_convert_obj[4]

        # add all the rules/ scenario definitions
        for sr in scenario_rules:
            sr.parent = grammar_obj
            grammar_obj.add_child(sr)

        return grammar_obj


class LanguageGrammar(Grammar):
    criterion_rule_alias = RuleAlias(LanguageToken)
    rule = Chain([
        criterion_rule_alias,
        RuleAlias(EndOfLineToken),
    ])
    convert_cls = Language

    def get_convert_kwargs(self, rule_output):
        return {'language': rule_output[0].token.locale}


class GherkinDocumentGrammar(Grammar):
    rule = Chain([
        Optional(LanguageGrammar()),
        Optional(FeatureGrammar()),
        RuleAlias(EOFToken),
    ])
    name = 'Gherkin document'
    convert_cls = GherkinDocument

    def prepare_converted_object(self, rule_convert_obj, grammar_obj: GherkinDocument):
        feature = rule_convert_obj[1]

        # set the feature if it exists
        if feature:
            grammar_obj.set_feature(feature)
            feature.parent = grammar_obj

        return grammar_obj
