# language: de
Funktionalität: Tests
  Grundlage:
    Gegeben sei ein Benutzer Alice mit dem Benutzernamen alice, der Email a@local.local und dem Passwort Haus1234

  Szenario: Ändern von ToDo - anderer Nutzer
    Gegeben sei ein Benutzer Bob mit dem Benutzernamen Bob
    Und folgende To-Dos
      | text | number | owner |
      | qwe  | 123    | alice |
      | qwe  | tre    | alice |
