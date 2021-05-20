Feature: Highlander

  Rule: There can be only One

    Example: Only One -- More than one alive
      Given there are 3 ninjas
      And there are more than one ninja alive
      * 2 ninjas meet, they will fight
      Then one ninja dies (but not me)
      * there is one ninja less alive

    Example: Only One -- One alive
      Given there is only 1 ninja alive
      But there is one ninja less alive
      # this step text already exists but only in a different scenario, so it is valid
      * one ninja dies (but not me)
      Then he (or she) will live forever ;-)
