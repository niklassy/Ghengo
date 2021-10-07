# language: de
Funktionalität: Abgebrochene Aufträge
  Szenario: Abgebrochene Aufträge nicht in Liste
    Gegeben sei eine Benutzerin Alice
    Und ein Auftrag, der nicht aktiv ist
    Wenn Alice die Liste der Aufträge holt
    Dann sollte die Liste keine Einträge haben

 Szenario: Abgebrochene Aufträge nicht in Details
    Gegeben sei eine Benutzerin Alice
    Und ein inaktiver Auftrag 1
    Wenn Alice den Auftrag 1 holt
    Dann sollte die Antwort den Status 404 haben

  Szenario: Abgebrochene Aufträge nicht löschbar
    Gegeben sei eine Benutzerin Alice
    Und ein Auftrag 1, der nicht aktiv ist
    Wenn Alice den Auftrag 1 löscht
    Dann sollte die Antwort den Status 404 haben
