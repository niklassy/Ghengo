# language: de
Funktionalität: Reference
#  Grundlage:
#   Gegeben sei ein Benutzer Alice mit dem Namen alice, der Email a@local.local

#  Szenario: Permission in Text
#    Gegeben seien der Benutzer Bob mit der Benutzerberechtigung "Auftrag hinzufügen"
#    Und Bob das Passwort "Admin123" hat
#    Und einen Auftrag 1
#    Wenn Alice einen Auftrag erstellt, der keine Kohle nutzt mit dem Besitzer 1

#  Szenario: M2M Relation
    #Gegeben sei ein Todo 1
    #Und ein Todo 2
#    Wenn Alice einen Auftrag mit den Sammlungen 1 und 2 erstellt


#  Szenario: M2M Model
#    Gegeben sei ein Auftrag 1, der Fußball spielt und fliegt
#    Und ein Auftrag 2
#    Und ein ToDo mit den Aufträgen 1 und 2

  Szenario: file
    Gegeben sei eine Text Datei "foo"
      | content | name |
      | asdasd  | abc  |
      | qweqwe  | def  |

  Szenario: file
    Gegeben sei eine Photoshop Datei "foo" mit dem Namen "Test" und dem Inhalt "Blubb" und dem Laden "test"
#    Wenn Alice einen Auftrag mit der Datei "foo" erstellt

#  Szenario: Ändern von ToDo - anderer Nutzer
#    Gegeben seien der Benutzer Bob mit der Benutzerberechtigung "order.add_order"
#    Und Bob das Passwort "Admin123" hat
#    Und einen Auftrag 1
#    Wenn Alice einen Auftrag erstellt, der keine Kohle nutzt mit dem Besitzer 1
