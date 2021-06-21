# language: de
Funktionalität: Tests
  Grundlage:
   Gegeben sei ein Benutzer Alice mit dem Namen alice, der Email a@local.local und dem Passwort Haus1234

  Szenario: Ändern von ToDo - anderer Nutzer
    Gegeben seien die To-Dos, die nicht aus dem anderen System kommen
      | text | number | owner |
      | qwe  | 123123123123123123123123123123123123123123123123123123123123    | alice |
      | qwe  | 123123123123123123123123123123123123123123123123123123123123    | alice |
