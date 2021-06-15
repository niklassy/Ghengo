# language: de
Funktionalität: Tests
  Grundlage:
    Gegeben sei ein Benutzer Alice mit dem Benutzernamen alice, der Email a@local.local und dem Passwort Haus1234

  Szenario: Ändern von ToDo - anderer Nutzer
    Gegeben sei eine Abrechnung 1 mit einer Summe von 30 und mit "Mein Titel" als Titel
    Und folgende Aufträge, die Alice als Besitzerin haben
      | text | number | owner |
      | qwe  | 123    | alice |
      | qwe  | tre    | alice |
