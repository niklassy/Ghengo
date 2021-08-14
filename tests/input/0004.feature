# language: de
Funktionalität:
  Hintergrund:
    Gegeben sei ein Auftrag mit dem Namen "foo"
  Szenario: file and use in order
    Wenn die Auftragsliste geholt wird
    Dann sollte die Antwort den Status 200 haben
    Und die Liste sollte einen Eintrag haben
    Und der erste Eintrag sollte den Namen "foo" haben
  Szenario:
    Gegeben sei ein Auftrag 2 mit dem Namen "baz"
    Wenn die Auftragsliste geholt wird
    Dann sollte die Liste zwei Einträge haben
    Und der zweite Eintrag sollte den Namen "baz" haben

