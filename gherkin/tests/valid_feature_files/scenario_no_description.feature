Feature: Highlander

  Rule: There can be only One

    Scenario:
      Given there are 3 ninjas
      And there are more than one ninja alive
      When 2 ninjas meet, they will fight
      Then one ninja dies (but not me)
      And there is one ninja less alive

    Example:
      Given there is only 1 ninja alive
      Then he (or she) will live forever ;-)
