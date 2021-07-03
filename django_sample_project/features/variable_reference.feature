# language: de
Funktionalität: Reference
  Grundlage:
   Gegeben sei ein Benutzer Alice mit dem Namen alice, der Email a@local.local

  Szenario: Ändern von ToDo - anderer Nutzer
    Gegeben seien der Benutzer Bob mit der Benutzerberechtigung "order.add_order"
    Und Bob das Passwort "Admin123" hat
    Und einen Auftrag 1
    Wenn Alice einen Auftrag erstellt, der keine Kohle nutzt mit dem Besitzer 1
