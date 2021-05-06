from gherkin.compiler.compiler import GherkinCompiler

feature_string = """# language en

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
                ```
            And qweqwe
            When qwe
            Then kjasd
            
        Scenario Outline: mal was anderes
            Given there are <start> cucumbers
            When I eat <eat> cucumbers
            Then I should have <left> cucumbers
            
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
    c = GherkinCompiler(test)
    a = c.compile()
    # a = Feature(feature_string)
    b = 1

