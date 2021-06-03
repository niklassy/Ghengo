from django_meta.project import DjangoProject
from generate.suite import TestCase, ModelFactoryExpression, Kwarg, AssignmentStatement, Variable, TestSuite
from gherkin.compiler import GherkinToPyTestCompiler
from nlp.django import get_model_field_by_text, get_model_from_text, handle_given
# from nlp.tokenize import tokenize, de_nlp, en_nlp
from translate import Translator

from nlp.setup import Nlp
from nlp.utils import *

feature_string = """# language: en

@tag1 @tag2
Feature: Ich bin etwas

    # asdasd
    Hier folgt dann eine Beschreibung.
    
    Rule: testser
    
        Background:
            Given wer
            
        Scenario: asd
            Given qwe
                ```
                Hier ist ein DocString
                Der auch etwas länger ist
                ```
            And qweqwe
            When rewqq
            Then kjasd
            
        Scenario Outline: mal was anderes
            Given there are <start> cucumbers
            When I eat <eat> cucumbers
            Then I should have <left> cucumbers
            
            @test1
            Examples:
            | start | eat | left |
            |    12 |   5 |    7 |
            |    20 |   5 |   15 |
            
            @test2
            Examples:
            | start | eat | left |
            |    12 |   5 |    7 |
            |    20 |   5 |   15 | 
"""

invalid_doc = """
Feature: asd
    asdasd
    asdasd
    
    Rule: asd
    
        Scenario: asd
            Given ew
            And qwe
            When qwe
            Then asd
        
        Scenario: qwe
"""

test = """
Feature: asd

    qweqwe
    qwe
    
    # asasdda
    
    Scenario: asd
"""


if __name__ == '__main__':
    """
    Können leider nicht die Library verwenden, weil sie scheinbar Probleme hat und weil wir sämtliche Informationen
    wie Kommentare behalten wollen, für weitere Informationen in der Zukunft.
    
    Test
    """
    project = DjangoProject('django_sample_project.apps.config.settings')
    a = project.get_models(include_django=True, as_interface=True)
    # w = tokenize('Ich bin ein neuer Text, den ich überprüfe.')
    b = 1

    c = GherkinToPyTestCompiler()
    a = c.compile_text(feature_string)
    ast = c.compile_file('django_sample_project/features/todo_crud.feature')
    compiled = []

    # p = get_model_field_by_text('de', 'Vorname', project.get_models(as_interface=True)[0])
    # p2 = get_model_field_by_text('de', 'Name', project.get_models(as_interface=True)[0])
    order_model = get_model_from_text('de', 'Auftrag', project)

    asd = handle_given(project, 'de', ast.feature.children[6].steps[2])

    # for scenario in d.feature.children:
    #     for step in scenario.steps:
    #         compiled.append(Nlp.for_language('de')(str(step)))
    suite = TestSuite(ast.feature.name if ast.feature else '')
    tc = suite.add_test_case()
    tc_1 = suite.add_test_case()
    tc_2 = suite.add_test_case()
    factory_ex = ModelFactoryExpression(order_model, [Kwarg('name', 'alice'), Kwarg('test', 'bob')])
    tc.add_statement(AssignmentStatement(factory_ex, Variable('order')))
    b = 1


