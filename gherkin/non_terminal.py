from gherkin.compiler_base.exception import NonTerminalInvalid
from gherkin.compiler_base.rule.utils import IndentBlock
from gherkin.compiler_base.symbol.non_terminal import NonTerminal
from gherkin.compiler_base.rule.operator import Chain, OneOf, Repeatable, Optional
from gherkin.compiler_base.symbol.terminal import TerminalSymbol
from gherkin.compiler_base.wrapper import TokenWrapper
from gherkin.token import LanguageToken, FeatureToken, EOFToken, DescriptionToken, RuleToken, ScenarioToken, \
    EndOfLineToken, TagToken, GivenToken, AndToken, ButToken, WhenToken, ThenToken, BackgroundToken, \
    DocStringToken, DataTableToken, ExamplesToken, ScenarioOutlineToken
from gherkin.ast import GherkinDocument, Language, \
    Feature, Description, Tag, Background, \
    DocString, DataTable, TableCell, TableRow, \
    And, But, When, Given, Then, \
    ScenarioOutline, Rule, Scenario, Examples
from settings import Settings


"""
Können leider nicht die Library verwenden, weil sie scheinbar Probleme hat und weil wir sämtliche Informationen
wie Kommentare behalten wollen, für weitere Informationen in der Zukunft.
"""


class DescriptionNonTerminal(NonTerminal):
    criterion_terminal_symbol = TerminalSymbol(DescriptionToken)
    rule = Chain([
        criterion_terminal_symbol,
        TerminalSymbol(EndOfLineToken),
    ])
    convert_cls = Description

    def get_convert_kwargs(self, rule_output):
        return {
            'text': rule_output[0].token.text,
        }


class DescriptionChainNonTerminal(NonTerminal):
    """
    There is a common pattern where a text can follow a keyword with more descriptions afterwards.
    This happens e.g. when defining a scenario:

    Scenario: name
        description of that scenario

    This is a wrapper to avoid code duplication. It won't result in a instance of an object for the AST though.
    """
    criterion_terminal_symbol = TerminalSymbol(DescriptionToken)
    rule = OneOf([
        Chain([TerminalSymbol(EndOfLineToken), Repeatable(DescriptionNonTerminal(), minimum=0)]),
        Repeatable(DescriptionNonTerminal()),
    ])

    def sequence_to_object(self, sequence, index=0):
        """
        Since descriptions are used in several places to define the name and description of Grammars, this function
        can be used to determine the name and the description from a list of ASTDescription objects.

        The input can be in the format:
        [Description]
        OR
        [EndOfLineTokenWrapper, [Description]]
        """
        rule_tree = self.get_rule_sequence_to_object(sequence, index)

        if not isinstance(rule_tree, list):
            return None, None

        # if the second entry in the list is a list, it holds all the descriptions
        if len(rule_tree) > 1 and isinstance(rule_tree[1], list):
            name = None
            descriptions = rule_tree[1]
        # if a list of descriptions is passed instead, the first entry holds the name and the
        # rest the descriptions
        else:
            name = rule_tree[0].text
            descriptions = rule_tree[1:]

        if len(descriptions) > 0:
            return name, ' '.join(d.text for d in descriptions)

        return name, None


class TagsNonTerminal(NonTerminal):
    criterion_terminal_symbol = TerminalSymbol(TagToken)
    rule = Chain([
        Repeatable(criterion_terminal_symbol),
        TerminalSymbol(EndOfLineToken),
    ])
    convert_cls = Tag

    def sequence_to_object(self, sequence, index=0):
        tags = []
        rule_tree = self.get_rule_sequence_to_object(sequence, index)

        for tag in rule_tree[0]:
            tags.append(self.convert_cls(tag.token.text_without_keyword))

        return tags


class DocStringNonTerminal(NonTerminal):
    criterion_terminal_symbol = TerminalSymbol(DocStringToken)
    rule = Chain([
        criterion_terminal_symbol,
        TerminalSymbol(EndOfLineToken),
        Repeatable(DescriptionNonTerminal(), minimum=0),
        criterion_terminal_symbol,
        TerminalSymbol(EndOfLineToken),
    ])
    convert_cls = DocString

    def get_convert_kwargs(self, rule_output):
        descriptions = rule_output[2]

        if len(descriptions) > 0:
            text = ' '.join([d.text for d in descriptions])
        else:
            text = ''

        return {'text': text}


class DataTableNonTerminal(NonTerminal):
    criterion_terminal_symbol = TerminalSymbol(DataTableToken)
    rule = Chain([
        Repeatable(Chain([
            criterion_terminal_symbol,
            TerminalSymbol(EndOfLineToken),
        ]), minimum=2),
    ])
    convert_cls = DataTable

    @classmethod
    def get_minimal_sequence(cls):
        return [DataTableToken, EndOfLineToken, DataTableToken, EndOfLineToken]

    def _validate_sequence(self, sequence, index):
        """Make sure that every row has the same amount of columns."""
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
                raise NonTerminalInvalid(
                    'All rows in a data table must have the same amount of columns. {}'.format(place_to_search),
                    grammar=self,
                    suggested_tokens=[],
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


class AndButNonTerminalBase(NonTerminal):
    def _get_rule(self):
        return Chain([
            self.criterion_terminal_symbol,
            TerminalSymbol(DescriptionToken),
            TerminalSymbol(EndOfLineToken),
            IndentBlock(
                Optional(OneOf([
                    DocStringNonTerminal(),
                    DataTableNonTerminal(),
                ])),
            ),
        ])

    def get_convert_kwargs(self, rule_output):
        return {
            'text': rule_output[1].token.text,
            'keyword': rule_output[0].token.matched_keyword,
            'argument': rule_output[3],
        }


class AndNonTerminal(AndButNonTerminalBase):
    criterion_terminal_symbol = TerminalSymbol(AndToken)
    convert_cls = And


class ButNonTerminal(AndButNonTerminalBase):
    criterion_terminal_symbol = TerminalSymbol(ButToken)
    convert_cls = But


class TagsGrammarMixin(object):
    def prepare_converted_object(self, rule_output, obj):
        obj = super().prepare_converted_object(rule_output, obj)

        tags = rule_output[0]
        if tags and isinstance(tags, list):
            for tag in tags:
                obj.add_tag(tag)

        return obj


class ExamplesNonTerminal(TagsGrammarMixin, NonTerminal):
    criterion_terminal_symbol = TerminalSymbol(ExamplesToken)
    rule = Chain([
        Optional(TagsNonTerminal()),
        criterion_terminal_symbol,
        DescriptionChainNonTerminal(),
        IndentBlock(
            DataTableNonTerminal(),
        ),
    ])
    convert_cls = Examples

    @classmethod
    def get_minimal_sequence(cls):
        return [ExamplesToken, EndOfLineToken] + DataTableNonTerminal.get_minimal_sequence()

    def get_convert_kwargs(self, rule_output):
        name, description = rule_output[2]

        return {
            'keyword': rule_output[1].token.matched_keyword,
            'name': name,
            'description': description,
            'datatable': rule_output[3]
        }


class GivenWhenThenBase(NonTerminal):
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


class GivenNonTerminal(GivenWhenThenBase):
    criterion_terminal_symbol = TerminalSymbol(GivenToken)
    rule = Chain([
        criterion_terminal_symbol,
        TerminalSymbol(DescriptionToken),
        TerminalSymbol(EndOfLineToken),
        Optional(OneOf([
            DocStringNonTerminal(),
            DataTableNonTerminal(),
        ])),
        Repeatable(OneOf([AndNonTerminal(), ButNonTerminal()]), minimum=0),
    ])
    convert_cls = Given

    @classmethod
    def get_minimal_sequence(cls):
        return [GivenToken, DescriptionToken, EndOfLineToken]


class WhenNonTerminal(GivenWhenThenBase):
    criterion_terminal_symbol = TerminalSymbol(WhenToken)
    rule = Chain([
        criterion_terminal_symbol,
        TerminalSymbol(DescriptionToken),
        TerminalSymbol(EndOfLineToken),
        Optional(OneOf([
            DocStringNonTerminal(),
            DataTableNonTerminal(),
        ])),
        Repeatable(OneOf([AndNonTerminal(), ButNonTerminal()]), minimum=0),
    ])
    convert_cls = When

    @classmethod
    def get_minimal_sequence(cls):
        return [WhenToken, DescriptionToken, EndOfLineToken]


class ThenNonTerminal(GivenWhenThenBase):
    criterion_terminal_symbol = TerminalSymbol(ThenToken)
    rule = Chain([
        criterion_terminal_symbol,
        TerminalSymbol(DescriptionToken),
        TerminalSymbol(EndOfLineToken),
        Optional(OneOf([
            DocStringNonTerminal(),
            DataTableNonTerminal(),
        ])),
        Repeatable(OneOf([AndNonTerminal(), ButNonTerminal()]), minimum=0),
    ])
    convert_cls = Then

    @classmethod
    def get_minimal_sequence(cls):
        return [ThenToken, DescriptionToken, EndOfLineToken]


class StepsNonTerminal(NonTerminal):
    rule = Chain([
        Repeatable(GivenNonTerminal(), minimum=0, show_in_autocomplete=True),
        Repeatable(WhenNonTerminal(), minimum=0, show_in_autocomplete=True),
        Repeatable(ThenNonTerminal(), minimum=0, show_in_autocomplete=True),
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
            raise NonTerminalInvalid(
                'You must use at least one Given, When or Then. {}'.format(place_to_search),
                grammar=self,
                suggested_tokens=[GivenToken, WhenToken, ThenToken]
            )

        return new_index

    def used_by_sequence_area(self, sequence, start_index, end_index):
        given = GivenNonTerminal().used_by_sequence_area(sequence, start_index, end_index)
        when = WhenNonTerminal().used_by_sequence_area(sequence, start_index, end_index)
        then = ThenNonTerminal().used_by_sequence_area(sequence, start_index, end_index)

        return given or when or then

    def sequence_to_object(self, sequence, index=0):
        output = []

        for step_list in self.get_rule_sequence_to_object(sequence, index):
            for step in step_list:
                output.append(step)

        return output


class ScenarioDefinitionNonTerminal(NonTerminal):
    description_index = 2

    def _validate_sequence(self, sequence, index):
        """
        In scenarios it is not valid to use the same text more than once.

        From docs: Keywords are not taken into account when looking for a step definition. This means you cannot
        have a Given, When, Then, And or But step with the same text as another step.

        => https://cucumber.io/docs/gherkin/reference/
        """
        new_index = super()._validate_sequence(sequence, index)

        # first get all descriptions that follow GIVEN, WHEN, THEN, AND or BUT since they hold the text
        descriptions = []
        for i, token_wrapper in enumerate(sequence[index:new_index]):
            if isinstance(token_wrapper.token, (GivenToken, WhenToken, ThenToken, AndToken, ButToken)):
                descriptions.append(sequence[index + i + 1])

        # extract all the texts
        texts = [d.token.text_without_keyword for d in descriptions]
        for i, text in enumerate(texts):
            # check if there is an earlier entry with the same text; if yet, raise an error
            if texts.index(text) < i:
                place_to_search = descriptions[i].get_place_to_search()
                raise NonTerminalInvalid(
                    'You must not use two different steps with the same text. {}'.format(place_to_search),
                    grammar=self,
                    suggested_tokens=[],
                )

        return new_index

    def get_convert_kwargs(self, rule_output):
        name, description = rule_output[self.description_index]

        return {
            'description': description,
            'keyword': rule_output[self.description_index - 1].token.matched_keyword,
            'name': name,
        }

    def get_steps_from_convert_obj(self, rule_convert_obj):
        raise NotImplementedError()

    def prepare_converted_object(self, rule_convert_obj, grammar_obj):
        steps = self.get_steps_from_convert_obj(rule_convert_obj)

        # add each step to the definition
        for step in steps:
            grammar_obj.add_step(step)

        return grammar_obj


class ScenarioOutlineNonTerminal(TagsGrammarMixin, ScenarioDefinitionNonTerminal):
    criterion_terminal_symbol = TerminalSymbol(ScenarioOutlineToken)
    rule = Chain([
        Optional(TagsNonTerminal()),
        criterion_terminal_symbol,
        DescriptionChainNonTerminal(),
        IndentBlock([
            StepsNonTerminal(),
            Repeatable(ExamplesNonTerminal()),
        ]),
    ])
    convert_cls = ScenarioOutline

    @classmethod
    def get_minimal_sequence(cls):
        outline_sequence = [ScenarioOutlineToken, EndOfLineToken]
        return outline_sequence + GivenNonTerminal.get_minimal_sequence() + ExamplesNonTerminal.get_minimal_sequence()

    def get_steps_from_convert_obj(self, rule_convert_obj):
        return rule_convert_obj[3][0]

    def prepare_converted_object(self, rule_convert_obj, grammar_obj: ScenarioOutline):
        """In addition to the steps, we need to add the argument of the Examples here."""
        grammar_obj = super().prepare_converted_object(rule_convert_obj, grammar_obj)
        examples = rule_convert_obj[3][1]

        for example in examples:
            example.parent = grammar_obj
            grammar_obj.add_example(example)

        return grammar_obj


class ScenarioNonTerminal(TagsGrammarMixin, ScenarioDefinitionNonTerminal):
    criterion_terminal_symbol = TerminalSymbol(ScenarioToken)
    rule = Chain([
        Optional(TagsNonTerminal()),
        criterion_terminal_symbol,
        DescriptionChainNonTerminal(),
        IndentBlock(
            StepsNonTerminal(),
        ),
    ])
    convert_cls = Scenario

    @classmethod
    def get_minimal_sequence(cls):
        return [ScenarioToken, EndOfLineToken] + GivenNonTerminal.get_minimal_sequence()

    def get_steps_from_convert_obj(self, rule_convert_obj):
        return rule_convert_obj[3]


class BackgroundNonTerminal(ScenarioDefinitionNonTerminal):
    description_index = 1
    criterion_terminal_symbol = TerminalSymbol(BackgroundToken)
    rule = Chain([
        criterion_terminal_symbol,
        DescriptionChainNonTerminal(),
        IndentBlock(
            Repeatable(GivenNonTerminal()),
        ),
    ])
    convert_cls = Background

    def get_steps_from_convert_obj(self, rule_convert_obj):
        return rule_convert_obj[2]

    @classmethod
    def get_minimal_sequence(cls):
        return [BackgroundToken, EndOfLineToken] + GivenNonTerminal.get_minimal_sequence()


class RuleNonTerminal(TagsGrammarMixin, NonTerminal):
    criterion_terminal_symbol = TerminalSymbol(RuleToken)
    rule = Chain([
        Optional(TagsNonTerminal()),    # support was added some time ago (https://github.com/cucumber/common/pull/1356)
        criterion_terminal_symbol,
        DescriptionChainNonTerminal(),
        IndentBlock([
            Optional(BackgroundNonTerminal()),
            Repeatable(OneOf([
                ScenarioNonTerminal(),
                ScenarioOutlineNonTerminal(),
            ]))
        ]),
    ])
    convert_cls = Rule

    @classmethod
    def get_minimal_sequence(cls):
        return [RuleToken, EndOfLineToken] + ScenarioNonTerminal.get_minimal_sequence()

    def get_convert_kwargs(self, rule_output):
        name, description = rule_output[2]

        return {
            'description': description,
            'keyword': rule_output[1].token.matched_keyword,
            'name': name,
            'background': rule_output[3][0],
        }

    def prepare_converted_object(self, rule_convert_obj, grammar_obj: Rule):
        # set tags
        grammar_obj = super().prepare_converted_object(rule_convert_obj, grammar_obj)

        # set all the children/ scenario definitions
        for sr in rule_convert_obj[3][1]:
            sr.parent = grammar_obj
            grammar_obj.add_scenario_definition(sr)

        return grammar_obj


class FeatureNonTerminal(TagsGrammarMixin, NonTerminal):
    criterion_terminal_symbol = TerminalSymbol(FeatureToken)
    rule = Chain([
        Optional(TagsNonTerminal()),
        criterion_terminal_symbol,
        DescriptionChainNonTerminal(),
        IndentBlock([
            Optional(BackgroundNonTerminal()),
            OneOf([
                Repeatable(RuleNonTerminal()),
                Repeatable(OneOf([
                    ScenarioNonTerminal(),
                    ScenarioOutlineNonTerminal(),
                ])),
            ]),
        ]),
    ])
    convert_cls = Feature

    @classmethod
    def get_minimal_sequence(cls):
        return [FeatureToken, EndOfLineToken] + RuleNonTerminal.get_minimal_sequence()

    def get_convert_kwargs(self, rule_output):
        name, description = rule_output[2]

        return {
            'description': description,
            'keyword': rule_output[1].token.matched_keyword,
            'name': name,
            'language': Settings.language,
            'background': rule_output[3][0],
        }

    def prepare_converted_object(self, rule_convert_obj: [TokenWrapper], grammar_obj: Feature):
        grammar_obj = super().prepare_converted_object(rule_convert_obj, grammar_obj)
        scenario_rules = rule_convert_obj[3][1]

        # add all the rules/ scenario definitions
        for sr in scenario_rules:
            sr.parent = grammar_obj
            grammar_obj.add_child(sr)

        return grammar_obj


class LanguageNonTerminal(NonTerminal):
    criterion_terminal_symbol = TerminalSymbol(LanguageToken)
    rule = Chain([
        criterion_terminal_symbol,
        TerminalSymbol(EndOfLineToken),
    ])
    convert_cls = Language

    def get_convert_kwargs(self, rule_output):
        return {'language': rule_output[0].token.locale}


class GherkinDocumentNonTerminal(NonTerminal):
    rule = Chain([
        Optional(LanguageNonTerminal()),
        Optional(FeatureNonTerminal(), show_in_autocomplete=True),
        TerminalSymbol(EOFToken),
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
