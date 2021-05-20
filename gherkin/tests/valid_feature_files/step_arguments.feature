Feature: Highlander

  @tag1 @tag2
  Rule: There can be only One

    Example: Only One -- More than one alive
      Given there are 3 ninjas
      """
      Das ist ist ein Step Argument
      """
      And there are more than one ninja alive
      | abc | def |
      | val1 | val2 |
      When 2 ninjas meet, they will fight
      Then one ninja dies (but not me)
      And there is one ninja less alive

    Example: Only One -- One alive
      Given there is only 1 ninja alive
      Then he (or she) will live forever ;-)
