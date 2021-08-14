# language: de
Funktionalität: Reference
  Szenario: check single response entry
    Gegeben sei ein Auftrag 1 mit dem Namen "foo"
    Wenn die Details von Auftrag 1 geholt werden
    Dann sollte die Antwort den Namen "foo" enthalten
    Und die Antwort sollte den PK 1 haben
