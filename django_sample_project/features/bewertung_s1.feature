# language: de
Funktionalität: Anfragen für Aufträge
  Szenario: Auftragsliste ohne Authentifizierung
    Wenn die Liste der Aufträge geholt wird
    Dann sollte die Antwort keine Einträge haben

  Szenario: Nutzer holt Auftragsliste
    Gegeben sei ein Benutzer Alice mit dem Vornamen Alice
    Und ein Auftrag mit dem Besitzer Alice und der Nummer 1
    Wenn Alice die Liste der Aufträge holt
    Dann sollte die Antwort einen Auftrag enthalten
    Und der erste Eintrag sollte die Nummer 1 haben

  Szenario: nur eigene Aufträge sichtbar
    Gegeben sei ein Benutzer Alice
    Und ein Auftrag mit dem Besitzer Alice
    Und ein Auftrag
    Wenn Alice die Liste der Aufträge holt
    Dann sollte die Antwort einen Auftrag enthalten

  Szenario: ohne Authentifizierung Auftrag erstellen
    Wenn ein Auftrag mit der Nummer 3 erstellt wird
    Dann sollte die Antwort den Status 400 haben
    Und den Fehler "Authentifizierung erforderlich" enthalten
    Und es sollte keine Aufträge geben

  Szenario: Auftrag erstellen funktioniert
    Gegeben sei ein Benutzer Bob
    Wenn Bob einen Auftrag mit der Nummer 3 und dem Besitzer Bob erstellt
    Dann sollte ein Auftrag mit der Nummer 3 und dem Besitzer Bob existieren
    Und die Antwort sollte den Besitzer Bob und die Nummer 3 enthalten

  Szenario: Auftrag löschen funktioniert
    Gegeben sei ein Benutzer Bob
    Und ein Auftrag 1 mit dem Benutzer Bob
    Wenn Bob einen Auftrag 1 löscht
    Dann sollte es keinen Auftrag geben

  Szenario: Auftrag löschen nicht existierender Auftrag
    Gegeben sei ein Benutzer Bob
    Wenn Bob den Auftrag mit dem PK 1 löscht
    Dann sollte die Antwort den Status 404 haben
