# language: de
Funktionalität: Erstellen, Löschen und Ändern von ToDos
  Grundlage: 
    Gegeben sei ein Benutzer Alice mit dem Benutzernamen alice, der Email a@local.local und dem Passwort Haus1234

  # TODO: add permissions??
  # TODO: add list call?

  Szenario: Erstellen von Todo - Erfolg
    Wenn Alice eine Anfrage zum Erstellen eines To-Do mit dem Text todo1 macht
    Dann sollte die Antwort den Status 200 haben
    Und es sollte ein ToDo-Objekt existieren mit dem Text todo1, das Alice zugeordnet ist
    
  Szenario: Erstellen von Todo - nicht eingeloggt
    Wenn ein anonymer Nutzer eine Anfrage zum Erstellen eines To-Do mit dem Text todo123 sendet
    Dann sollte die Antwort den Status 400 haben
    Und es sollte kein To-Do Objekt existieren
    
  Szenario: Ändern von ToDo - Erfolg
    Gegeben sei ein To-Do AliceToDo mit dem Text todo1, das Alice zugeordnet ist 
    Wenn Alice eine Anfrage zum Ändern des To-Do AliceToDo mit dem Text todo2 macht
    Dann sollte die Antwort den Status 200 haben
    Und das To-Do AliceToDo sollte den Text todo2 haben
  
  Szenario: Ändern von ToDo - anderer Nutzer
    Gegeben sei ein Benutzer Bob mit dem Benutzernamen Bob
    Und ein To-Do AliceToDo mit dem Text todo1, das Alice als Besitzer hat
    Wenn Bob eine Anfrage zum Ändern des To-Do AliceToDo mit dem Text todoBob macht
    Dann sollte die Antwort den status 400 haben
    Und das To-Do AliceToDo sollte den Text todo1 haben
    
  Szenario: Ändern von ToDo - nicht eingeloggt
    Gegeben sei ein To-Do AliceToDo mit dem Text todo1, das Alice zugeordnet ist 
    Wenn ein anonymer Nutzer eine Anfrage zum Ändern des To-Do AliceToDo mit dem Text todo123 sendet
    Dann sollte die Antwort den Status 400 haben
    Und das To-Do AliceToDo sollte den Text todo1 haben
    
  Szenario: Löschen eines ToDo - Erfolg
    Gegeben sei ein To-Do AliceToDo mit dem Text todo1, das Alice zugeordnet ist 
    Wenn Alice eine Anfrage zum Löschen des To-Do AliceToDo macht
    Dann sollte die Antwort den Status 200 haben
    Und das To-Do AliceToDo sollte nicht mehr existieren

  Szenario: Löschen eines ToDo - anderer Benutzer
    Gegeben sei ein Nutzer Bob mit dem Benutzernamen Bob
    Und ein Auftrag Order1 mit dem Namen hi123, der einem Benutzer Alice zugewiesen ist
    Wenn Bob eine Anfrage zum Löschen des To-Do AliceToDo macht
    Dann sollte die Antwort den Status 400 haben
    Und das To-Do AliceToDo sollte noch existieren

  Szenario: Löschen eines Todo - anonymer Benutzer
    Gegeben sei ein To-Do AliceToDo mit dem Text todo1, das Alice zugeordnet ist
    Wenn ein anonymer Benutzer eine Anfrage zum Löschen des To-Do AliceToDo macht
    Dann sollte die Antwort den Status 400 haben
    Und das To-Do AliceToDo sollte noch existieren
