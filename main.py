from django_meta.project import DjangoProject
from gherkin.compiler import GherkinToPyTestCompiler
from nlp.tokenize import tokenize

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
    w = tokenize('Ich bin ein neuer Text, den ich überprüfe.')
    b = 1

    # c = GherkinToPyTestCompiler()
    # a = c.compile_text(feature_string)
    # d = c.compile_file('test.feature')
    b = 1

