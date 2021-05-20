from gherkin.token import ExamplesToken, EndOfLineToken, DataTableToken, GivenToken, DescriptionToken, \
    WhenToken, ThenToken, BackgroundToken, ScenarioToken, ScenarioOutlineToken, RuleToken, FeatureToken

examples_sequence = [
    ExamplesToken(None, None),
    EndOfLineToken(None, None),
    DataTableToken('|n|q|', None),
    EndOfLineToken(None, None),
    DataTableToken('|a|b|', None),
    EndOfLineToken(None, None),
]

given_sequence = [
    GivenToken('Given asd', None),
    DescriptionToken(None, None),
    EndOfLineToken(None, None),
]

when_sequence = [
    WhenToken(None, None),
    DescriptionToken(None, None),
    EndOfLineToken(None, None),
]

then_sequence = [
    ThenToken(None, None),
    DescriptionToken(None, None),
    EndOfLineToken(None, None),
]

background_sequence = [
    BackgroundToken(None, None),
    DescriptionToken('name', None),
    EndOfLineToken(None, None),
    DescriptionToken('desc', None),
    EndOfLineToken(None, None),
] + given_sequence

scenario_sequence = [
    ScenarioToken(None, None),
    DescriptionToken('name', None),
    EndOfLineToken(None, None),
    DescriptionToken('desc', None),
    EndOfLineToken(None, None),
] + given_sequence

scenario_outline_sequence = [
    ScenarioOutlineToken(None, None),
    DescriptionToken('name', None),
    EndOfLineToken(None, None),
    DescriptionToken('desc', None),
    EndOfLineToken(None, None),
] + given_sequence + examples_sequence

rule_sequence = [
    RuleToken(None, None),
    DescriptionToken('name1', None),
    EndOfLineToken(None, None),
    DescriptionToken('desc1', None),
    EndOfLineToken(None, None),
] + scenario_sequence

feature_sequence = [
    FeatureToken(None, None),
    DescriptionToken('name123', None),
    EndOfLineToken(None, None),
    DescriptionToken('desc123', None),
    EndOfLineToken(None, None),
] + scenario_sequence
