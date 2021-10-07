# language: de
Funktionalität: Berechtigungen
  Szenario: Auftrag erstellen
    Gegeben sei ein Auftrag 1
    Und ein Benutzer Bob mit der Benutzerberechtigung "Kann Produkt erstellen"
    Wenn Bob einen Auftrag erstellt
    Dann sollte die Antwort den Status 200 haben
