# language: de
Funktionalität: Reference
  Grundlage:
    Gegeben sei ein Auftrag 1
  Szenario: previous model
    Wenn der Auftrag 1 so geändert wird, dass der Name "foo" ist
    Dann sollte es einen Auftrag geben, der den Namen "foo" geben
  Szenario:
    Wenn der Auftrag 1 so geändert wird, dass der Name "bar" ist
    Dann sollten Aufträge mit dem Namen "bar" existieren
