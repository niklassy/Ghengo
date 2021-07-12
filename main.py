import time

from django_meta.setup import setup_django
from nlp.setup import Nlp

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


if __name__ == '__main__':
    """
    Können leider nicht die Library verwenden, weil sie scheinbar Probleme hat und weil wir sämtliche Informationen
    wie Kommentare behalten wollen, für weitere Informationen in der Zukunft.
    """
    # first, setup django before importing the rest of the project, or else we would get errors from django that
    # the apps are not ready yet
    setup_django('django_sample_project.apps.config.settings')

    from django_meta.project import DjangoProject
    from gherkin.compiler import GherkinToPyTestCompiler

    DjangoProject('django_sample_project.apps.config.settings')
    c = GherkinToPyTestCompiler()
    file_ast = c.compile_file('django_sample_project/features/variable_reference.feature')
    Nlp.for_language('de')
    Nlp.for_language('en')

    start = time.time()
    c.export_as_file('generated_tests/')
    print('Done after {}'.format(time.time() - start))
