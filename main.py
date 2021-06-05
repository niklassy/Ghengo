from django_meta.project import DjangoProject
from generate.suite import TestCase, ModelFactoryExpression, Kwarg, AssignmentStatement, Variable, TestSuite
from gherkin.compiler import GherkinToPyTestCompiler
from nlp.django import get_model_field_by_text, get_model_from_text, handle_given
# from nlp.tokenize import tokenize, de_nlp, en_nlp
from translate import Translator

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
    """
    project = DjangoProject('django_sample_project.apps.config.settings')
    a = project.get_models(include_django=True, as_interface=True)
    # w = tokenize('Ich bin ein neuer Text, den ich überprüfe.')
    b = 1

    c = GherkinToPyTestCompiler()
    feature_ast = c.compile_text(feature_string)
    feature_code = c.export_as_text()
    c.export_as_file('generated_tests/')

    file_ast = c.compile_file('django_sample_project/features/todo_crud.feature')
    file_code = c.export_as_text()
    c.export_as_file('generated_tests/')

    order_model = get_model_from_text('de', 'Auftrag', project)

    suite = TestSuite(feature_ast.feature.name if feature_ast.feature else '')
    tc = suite.create_and_add_test_case('test')
    factory_ex_2 = ModelFactoryExpression(order_model, [Kwarg('name', 'alice'), Kwarg('test', 'bob')])
    tc.add_statement(AssignmentStatement(factory_ex_2, Variable('order_2')))
    tc = suite.create_and_add_test_case('new')
    factory_ex_2 = ModelFactoryExpression(order_model, [Kwarg('name', 'alice'), Kwarg('test', 'bob')])
    tc.add_statement(AssignmentStatement(factory_ex_2, Variable('order_2')))
    tc = suite.create_and_add_test_case('test4')
    factory_ex_2 = ModelFactoryExpression(order_model, [Kwarg('name', 'alice'), Kwarg('test', 'bob')])
    tc.add_statement(AssignmentStatement(factory_ex_2, Variable('order_2')))
    b = 1


