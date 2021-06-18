# language: de
Funktionalität: Tests
  Grundlage:
    Gegeben sei ein Benutzer Alice mit dem Benutzernamen alice, der Email a@local.local und dem Passwort Haus1234

  Szenario:
    Gegeben seien Aufträge mit Alice als Besitzerin
      | name | plays_soccer |
      | Test | true         |
      | Test2 | false         |
    Und ein Auftrag 2, der Fußball spielt
