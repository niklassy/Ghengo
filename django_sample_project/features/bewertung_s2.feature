# language: de
Funktionalität: Aktive Benutzer
  Szenario: Inaktive Benutzer können keine Aufträge holen
    Gegeben sei eine Benutzerin Alice, die nicht aktiv ist
    Wenn Alice die Liste der Aufträge holt
    Dann sollte die Antwort den Status 400 haben

  Szenario: Inaktive Benutzer können keine Aufträge erstellen
    Gegeben sei eine inaktive Benutzerin Alice
    Wenn Alice einen Auftrag erstellt
    Dann sollte die Antwort den Status 400 haben

  Szenario: Inaktive Benutzer können keine Aufträge löschen
    Gegeben sei eine Benutzerin Alice, die nicht aktiv ist
    Und ein Auftrag 1
    Wenn Alice den Auftrag 1 löscht
    Dann sollte die Antwort den Status 400 haben
