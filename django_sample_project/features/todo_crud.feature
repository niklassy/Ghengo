# language: de
Funktionalität: Erstellen, Löschen und Ändern von ToDos
  Grundlage:
    Gegeben sei ein Benutzer Alice mit dem Benutzernamen alice, der Email a@local.local und dem Passwort Haus1234

#  Szenario: Erstellen von Todo - Erfolg
#    Wenn Alice eine Anfrage zum Erstellen eines To-Do mit dem Text todo1 macht
#    Dann sollte die Antwort den Status 200 haben
#    Und es sollte ein ToDo-Objekt existieren mit dem Text todo1, das Alice zugeordnet ist
#
#  Szenario: Erstellen von Todo - nicht eingeloggt
#    Wenn ein anonymer Nutzer eine Anfrage zum Erstellen eines To-Do mit dem Text todo123 sendet
#    Dann sollte die Antwort den Status 400 haben
#    Und es sollte kein To-Do Objekt existieren

  Szenario: Ändern von ToDo - Erfolg
    Gegeben sei ein To-Do AliceToDo mit dem Text todo1, das nicht aus dem anderen System kommt und Alice als Besitzerin hat
#    Wenn Alice eine Anfrage zum Ändern des To-Do AliceToDo mit dem Text todo2 macht
#    Dann sollte die Antwort den Status 200 haben
#    Und das To-Do AliceToDo sollte den Text todo2 haben
#
  Szenario: Ändern von ToDo - anderer Nutzer
    Gegeben sei ein Benutzer Bob mit dem Benutzernamen Bob
    Und folgende To-Dos
      | text | number | owner |
      | qwe  | 123    | alice |
      | qwe  | tre    | alice |

  Szenario: M2M
    Gegeben sei eine Produkt mit dem Namen iPhone

  Szenario: Mein neuer Test
    Gegeben sei ein Benutzer 1 mit dem "test" als Benutzernamen

  Szenario: Aufträge und Todos
    Gegeben sei ein Auftrag 1 mit "Auftrag 123" als Name
#    Und ein Auftrag 2
#    Und ein To-Do mit den Aufträgen 1 und 2
#    Wenn Bob eine Anfrage zum Ändern des To-Do AliceToDo mit dem Text todoBob macht
#    Dann sollte die Antwort den status 400 haben
#    Und das To-Do AliceToDo sollte den Text todo1 haben
#
  Szenario: Ändern von ToDo - nicht eingeloggt
    Gegeben sei ein To-Do AliceToDo mit dem Text todo1, das Alice als Besitzerin hat
#    Wenn ein anonymer Nutzer eine Anfrage zum Ändern des To-Do AliceToDo mit dem Text todo123 sendet
#    Dann sollte die Antwort den Status 400 haben
#    Und das To-Do AliceToDo sollte den Text todo1 haben
#
#  Szenario: Löschen eines ToDo - Erfolg
#    Gegeben sei ein To-Do AliceToDo mit dem Text todo1, das Alice zugeordnet ist
#    Wenn Alice eine Anfrage zum Löschen des To-Do AliceToDo macht
#    Dann sollte die Antwort den Status 200 haben
#    Und das To-Do AliceToDo sollte nicht mehr existieren
#
  Szenario: Löschen eines ToDo - anderer Benutzer
    Gegeben sei ein Nutzer Bob mit dem Benutzernamen Bob
    Und ein Auftrag Order1 mit dem Namen hi123, der Alice als Besitzerin hat
#    Wenn Bob eine Anfrage zum Löschen des To-Do AliceToDo macht
#    Dann sollte die Antwort den Status 400 haben
#    Und das To-Do AliceToDo sollte noch existieren
#
#  Szenario: Löschen eines Todo - anonymer Benutzer
#    Gegeben sei ein To-Do AliceToDo mit dem Text todo1, das Alice zugeordnet ist
#    Wenn ein anonymer Benutzer eine Anfrage zum Löschen des To-Do AliceToDo macht
#    Dann sollte die Antwort den Status 400 haben
#    Und das To-Do AliceToDo sollte noch existieren
#
#  Szenariogrundriss: Das ist ein Test
#    Gegeben sei ein Nutzer Bob mit dem Benutzernamen <test1> und der Email <test2>
#    Wenn Alice eine Anfrage zum Erstellen eines To-Do mit dem Text todo1 macht
#    Dann sollte die Antwort den Status 200 haben
#    Und es sollte ein ToDo-Objekt existieren mit dem Text todo1, das Alice zugeordnet ist
#
#    Beispiele:
#      |test1|test2|
#      |  12345678901234567890123456789012345678901234567890   |  123456789012345678901234567890123456789012345678901234567890  |
#      |  23   |  43  |
