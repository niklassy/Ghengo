# language: de
Funktionalität: Reference
#  Grundlage:
#   Gegeben sei ein Benutzer Alice mit dem Namen alice, der Email a@local.local

#  Szenario: Permission in Text
#    Gegeben seien der Benutzer Bob mit der Benutzerberechtigung "Auftrag hinzufügen"
#    Und Bob das Passwort "Admin123" hat
#    Und einen Auftrag 1
#    Wenn Alice einen Auftrag erstellt, der keine Kohle nutzt mit dem Besitzer 1

  Szenario: M2M Relation
    Gegeben sei ein Todo 1
    Und ein Todo 2
    Und ein Auftrag 1 mit den Todos 1 und 2


#  Szenario: Ändern von ToDo - anderer Nutzer
#    Gegeben seien der Benutzer Bob mit der Benutzerberechtigung "order.add_order"
#    Und Bob das Passwort "Admin123" hat
#    Und einen Auftrag 1
#    Wenn Alice einen Auftrag erstellt, der keine Kohle nutzt mit dem Besitzer 1
