from gherkin.ast import GherkinDocument, Feature, Comment, HasTagsMixin, HasBackgroundMixin, Background, Step, \
    ScenarioDefinition, ParentStep, SubStep, ScenarioOutline, Examples, Scenario, TableCell, TableRow, DataTable, \
    Rule, DocString
from test_utils import assert_callable_raises


def test_gherkin_document():
    """Check that all methods of GherkinDocument work."""
    doc = GherkinDocument()
    assert len(doc.comments) == 0
    assert doc.feature is None

    c = Comment('asd')
    doc.add_comment(c)
    assert c in doc.comments

    f = Feature(None, None, None, None)
    doc.set_feature(f)

    assert f == doc.feature
    doc.set_feature(None)
    assert doc.feature is None


def test_has_tags_mixin():
    """Check that the tags mixin works with inheritance."""
    mixin = HasTagsMixin()
    mixin_parent = HasTagsMixin()
    mixin.parent = mixin_parent

    mixin.add_tag(123)
    assert mixin.tags == [123]

    mixin_parent.add_tag(345)
    assert mixin.tags == [123, 345]


def test_has_background_mixin():
    """Check if the background mixin returns the correct steps - the ones from the parent."""
    b = Background(None, None, None)
    step_1 = Step(None, None)
    step_2 = Step(None, None)

    b.add_step(step_1)
    mixin = HasBackgroundMixin(background=b)
    assert mixin.steps == [step_1]
    b.add_step(step_2)
    assert mixin.steps == [step_1, step_2]


def test_feature():
    """Check that a feature sets all its values correctly and has tags and background."""
    b = Background(None, None, None)
    feature = Feature('lan', 'key', 'name', 'desc', b)
    assert feature.language == 'lan'
    assert feature.keyword == 'key'
    assert feature.name == 'name'
    assert feature.description == 'desc'
    assert feature.background == b
    assert isinstance(feature, HasTagsMixin)
    assert isinstance(feature, HasBackgroundMixin)

    feature.add_child(123)
    assert feature.children == [123]


def test_scenario_definition():
    """Check that the scenario definition handles steps correctly and sets values from __init__."""
    sc_def = ScenarioDefinition('key', 'name', 'desc')
    assert sc_def.keyword == 'key'
    assert sc_def.name == 'name'
    assert sc_def.description == 'desc'
    assert sc_def.steps == []

    assert_callable_raises(sc_def.add_step, ValueError, args=[123])
    step = Step(None, None)
    sc_def.add_step(step)
    assert sc_def.steps == [step]

    parent_step = ParentStep(None, None)
    child_step = SubStep(None, None)
    parent_step.add_sub_step(child_step)
    sc_def.add_step(parent_step)
    assert sc_def.steps == [step, parent_step, child_step]


def test_background():
    """For now, background does not do anything yet. So just check if it inherits correctly."""
    assert isinstance(Background(None, None, None), ScenarioDefinition)


def test_scenario_outline():
    """ScenarioOutlines have examples. Make sure that they are handled correctly."""
    ex = Examples(None, None, None, None)
    ex_2 = Examples(None, None, None, None)
    sc_out = ScenarioOutline('key', 'name', 'desc')
    assert sc_out.keyword == 'key'
    assert sc_out.name == 'name'
    assert sc_out.description == 'desc'
    assert sc_out.examples == []
    assert isinstance(sc_out, HasTagsMixin)
    assert isinstance(sc_out, ScenarioDefinition)

    sc_out.add_example(ex)
    assert sc_out.examples == [ex]
    sc_out.add_example(ex_2)
    assert sc_out.examples == [ex, ex_2]


def test_scenario():
    """For now scenarios only inherit from parents."""
    scenario = Scenario('key', 'name', 'desc')
    assert scenario.keyword == 'key'
    assert scenario.name == 'name'
    assert scenario.description == 'desc'
    assert isinstance(scenario, HasTagsMixin)
    assert isinstance(scenario, ScenarioDefinition)


def test_step_argument():
    """For now, no implementation needed here but there most likely will be something in the future."""
    pass


def test_table_row():
    """Check that a table row saves and handles cells correctly."""
    tc1 = TableCell('val1')
    tc2 = TableCell('val2')
    tc3 = TableCell('val3')

    tr = TableRow(cells=[tc1, tc2, tc3])
    assert tr.cells == [tc1, tc2, tc3]
    assert tr.get_value_at(0) == 'val1'
    assert tr.get_value_at(1) == 'val2'
    assert tr.get_value_at(2) == 'val3'


def test_data_table():
    """Check that a data table sets the header and the rows are set correctly and can be extracted."""
    tc11 = TableCell('header1')
    tc12 = TableCell('header2')
    tc21 = TableCell('val3')
    tc22 = TableCell('val4')
    tc31 = TableCell('val5')
    tc32 = TableCell('val6')

    tr1 = TableRow(cells=[tc11, tc12])
    tr2 = TableRow(cells=[tc21, tc22])
    tr3 = TableRow(cells=[tc31, tc32])

    dt = DataTable(header=tr1, rows=[tr2, tr3])
    assert dt.header == tr1
    assert dt.rows == [tr2, tr3]
    assert dt.get_row_at(0) == tr2
    assert dt.get_row_at(1) == tr3
    assert dt.get_values() == {'header1': ['val3', 'val5'], 'header2': ['val4', 'val6']}


def test_examples():
    """Check that examples sets all the values correctly."""
    dt = DataTable(None)
    examples = Examples('key', 'name', 'desc', dt)
    assert examples.keyword == 'key'
    assert examples.name == 'name'
    assert examples.description == 'desc'
    assert examples.datatable == dt


def test_rule():
    """Check that a rule sets all the scenario definitions and the data that is passed to it."""
    b = Background(None, None, None)
    rule = Rule('key', 'name', 'desc', b)
    assert rule.keyword == 'key'
    assert rule.name == 'name'
    assert rule.description == 'desc'
    assert rule.background == b
    assert isinstance(rule, HasBackgroundMixin)
    assert isinstance(rule, HasTagsMixin)

    assert rule.scenario_definitions == []
    sd = ScenarioDefinition(None, None, None)
    rule.add_scenario_definition(sd)
    assert rule.scenario_definitions == [sd]

    assert_callable_raises(rule.add_scenario_definition, ValueError, args=['asdasd'])


def test_step():
    """Check that a step saves all data that is passed to it and that is extracts all argument names."""
    ds = DocString(None)
    step = Step('key', 'text', argument=ds)
    assert step.keyword == 'key'
    assert step.text == 'text'
    assert step.argument == ds
    assert Step('key', None).argument_names == []
    assert Step('key', 'test {name_1} {name_2} name_3').argument_names == ['name_1', 'name_2']


def test_parent_step():
    """Check that a parent step can have sub steps."""
    step = ParentStep('key', 'text')
    assert step.sub_steps == []
    sub_step = SubStep('key', 'text')
    step.add_sub_step(sub_step)
    assert step.sub_steps == [sub_step]
    assert sub_step.parent == step

    assert_callable_raises(step.add_sub_step, ValueError, args=[ParentStep(None, None)])
