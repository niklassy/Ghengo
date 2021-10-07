# language: de
Funktionalität: Berechtigungen
  Szenario: Produkt erstellen mit Berechtigung
    Gegeben sei ein Benutzer Bob mit der Benutzerberechtigung "Kann Produkt erstellen"
    Wenn Bob ein Produkt erstellt
    Dann sollte die Antwort den Status 200 haben

  Szenario: Produkt erstellen ohne Berechtigung
    Gegeben sei ein Benutzer Bob
    Wenn Bob ein Produkt erstellt
    Dann sollte die Antwort den Status 400 haben
    Und die Antwort sollte den Fehler "Ihnen fehlen die Berechtigungen" enthalten

  Szenario: Produkt bearbeiten mit Berechtigung
    Gegeben sei ein Benutzer Bob mit der Benutzerberechtigung "Kann Produkt bearbeiten"
    Und ein Produkt 1
    Wenn Bob in Produkt 1 den Namen "Briefmarke" setzt
    Dann sollte die Antwort den Status 200 haben

  Szenario: Produkt bearbeiten ohne Berechtigung
    Gegeben sei ein Benutzer Bob
    Und ein Produkt 1
    Wenn Bob in Produkt 1 den Namen "Briefmarke" setzt
    Dann sollte die Antwort den Status 400 haben
    Und die Antwort sollte den Fehler "Ihnen fehlen die Berechtigungen" enthalten
