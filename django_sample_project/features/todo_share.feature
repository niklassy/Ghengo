# language: de
Funktionalität: Teilen von ToDo

  Grundlage:
    Gegeben sei ein Benutzer Alice
    Und ein Benutzer Bob
    Und ein Benutzer Cedric
    Und Alice hat Bob als Freund
    Und Bob hat Alice als Freund
    Und ein To-Do AliceToDo mit dem Text "todo1", das Alice zugeordnet ist

  Szenario: anonymer Nutzer
    Wenn ein anonymer Nutzer eine Anfrage zum Teilen von AliceToDo mit Bob macht
    Dann sollte die Antwort den Status 400 haben

  Szenario: Teilen mit Freund - Erfolg
    Wenn Alice eine Anfrage zum Teilen von AliceToDo mit Bob macht
    Dann sollte die Antwort den Status 200 haben
    Und Bob sollte AliceToDo bei einer Anfrage zur Auflistung der To-Do sehen

  Szenario: Sichtbarkeit nach Teilen
    Wenn Alice eine Anfrage zum Teilen von AliceToDo mit Cedric macht
    Dann sollte die Antwort den Status 400 haben
    Und Cedric sollte AliceToDo bei einer Anfrage zur Auflistung der To-Do nicht sehen
