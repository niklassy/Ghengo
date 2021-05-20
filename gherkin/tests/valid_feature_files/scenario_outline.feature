Feature: Highlander

  Rule: There can be only One

    Scenario Outline: eating
    Given there are <start> cucumbers
    When I eat <eat> cucumbers
    Then I should have <left> cucumbers

  Examples:
    | start | eat | left |
    |    12 |   5 |    7 |
    |    20 |   5 |   15 |

    Example:
      Given there is only 1 ninja alive
      Then he (or she) will live forever ;-)
