# language: de
Funktionalität: Login
  Grundlage:
    Gegeben sei ein Nutzer Alice mit Email "a@local.local" und Passwort "Haus1234"

  Szenario: Valider Login
    Wenn Alice eine Anfrage an /login mit Email "a@local.local" und Passwort "Haus1234" macht
    Dann sollte die Antwort den Status 200 haben
    Und einen Token enthalten

  Szenario: Invalider Login
    Wenn Alice eine Anfrage an /login mit Email "a@local.local" und Passwort "AnderesPasswort" macht
    Dann sollte die Antwort den Status 400 haben
    Und sollte keinen Token enthalten
