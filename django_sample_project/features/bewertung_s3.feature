# language: de
Funktionalität: Produkte und Aufträge
  Szenario: Produkte löschen
    Gegeben sei ein Produkt 1 mit dem Namen "Briefmarke"
    Und ein Benutzer Bob
    Wenn Bob das Produkt 1 löscht
    Dann sollten keine Produkte existieren

  Szenario: Produkte erstellen
    Gegeben sei ein Benutzer Bob
    Wenn Bob ein Produkt mit dem Namen "Briefmarke" erstellt
    Dann sollte ein Produkt existieren

  Szenario: Produkte hinzufügen
    Gegeben sei ein Benutzer Bob
    Und ein Produkt 1
    Und ein Produkt 2
    Und ein Auftrag 1 mit den Produkten 1 und 2
    Und ein Produkt 3 mit dem Namen "Briefmarke"
    Wenn Bob dem Produkt 3 zu Auftrag 1 hinzufügt
    Dann sollte der Auftrag 1 die Produkte 1, 2 und 3 haben
