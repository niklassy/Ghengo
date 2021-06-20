# language: de
Funktionalität: Tests
  Grundlage:
    Gegeben sei ein Benutzer Alice mit dem Benutzernamen alice, der Email a@local.local und dem Passwort Haus1234

  Szenario: Ändern von ToDo - anderer Nutzer
    Gegeben sei ein Benutzer Bob mit dem Benutzernamen Bob
    Und die To-Do
      | text | number | owner |
      | qwe  | 123123123123123123123123123123123123123123123123123123123123    | alice |
      | qwe  | 123123123123123123123123123123123123123123123123123123123123    | alice |
