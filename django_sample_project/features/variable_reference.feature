# language: de
Funktionalität: Reference
#  Grundlage:
#   Gegeben sei ein Benutzer Alice mit dem Nachnamen "alice", der Email "a@local.local"

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

#  Szenario: file
#    Gegeben sei eine Text Datei "foo"
#      | content | name |
#      | asdasd  | abc  |
#      | qweqwe  | def  |

#  Szenario: file
#    Gegeben sei eine Word Datei "asd"
#    Und ein Auftrag mit dem Namen "Hallo"
#    Wenn Alice einen Auftrag mit der Datei "asd" erstellt

  Szenario: file
    Dann sollte der Benutzer mit dem Vornamen "Alice" und dem Nachnamen "Müller" den Wert "Blubb" haben
    Dann sollten Benutzer mit dem Vornamen "Alice" existieren

#    Wenn Alice ein Dach mit dem System 3 ändert

#  Szenario: Ändern von ToDo - anderer Nutzer
#    Gegeben seien der Benutzer Bob mit der Benutzerberechtigung "order.add_order"
#    Und Bob das Passwort "Admin123" hat
#    Und einen Auftrag 1
#    Wenn Alice einen Auftrag erstellt, der keine Kohle nutzt mit dem Besitzer 1
