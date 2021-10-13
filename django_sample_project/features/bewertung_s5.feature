# language: de
Funktionalität: Datenstrukturen
  Szenario: Variante 1
    Gegeben sei ein Benutzer Bob
    Wenn Bob einen Auftrag mit einem Item mit der Produkt-ID 1 und der Menge 1 erstellt
    Dann sollte die Antwort den Status 200 haben
    Und es sollte ein Item mit der Auftrags-ID 1 und der Menge 1 existieren

  Szenario: Variante 2
    Gegeben sei ein Benutzer Bob
    Wenn Bob einen Auftrag mit den Items '[{"quantity": 1, "product_id": 1}]' erstellt
    Dann sollte die Antwort den Status 200 haben
    Und es sollte ein Item mit der Auftrags-ID 1 und der Menge 1 existieren
