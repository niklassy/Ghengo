from gherkin.parser import GherkinCompiler

feature_string = """# language en

@tag1 @tag2
Feature: Ich bin etwas

    # asdasd
    Hier folgt dann eine Beschreibung.
    
    Rule: testser
    
        Background: asdasd
            Ich bin eine neue Information
            Bla Blubb
            
        Scenario: asd
            Given qwe
            And qweqwe
            When qwe
            Then kjasd
"""


if __name__ == '__main__':
    """
    Können leider nicht die Library verwenden, weil sie scheinbar Probleme hat und weil wir sämtliche Informationen
    wie Kommentare behalten wollen, für weitere Informationen in der Zukunft.
    """
    c = GherkinCompiler(feature_string)
    a = c.compile()
    # a = Feature(feature_string)
    b = 1

