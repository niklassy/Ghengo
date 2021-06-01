# language: de

Funktionalität: Registrierung

  Szenario: Valide Registrierung
    Wenn eine Anfrage an /register mit Passwort "Haus1234", Email "a@local.local" und Benutzername "test" gemacht wird
    Dann sollte die Antwort den Status 200 haben
    Und es sollte ein Benutzer mit dem Benutzernamen "test" existieren
    Und dieser Benutzer sollte die Email "a@local.local" haben
    Und dieser Benutzer sollte das Passwort "Haus1234" haben

  Szenario: Benutzername bereits vergeben
    Gegeben sei ein Benutzer Alice mit dem Benutzernamen "test" und der Email "alice@local.local"
    Wenn eine Anfrage an /register mit Passwort "Haus1234", Email "a@local.local" und Benutzername "test" gemacht wird
    Dann sollte die Antwort den Status 400 haben
    Und die Fehlermeldung "bereits vergeben" enthalten

  Szenario: Email bereits vergeben
    Gegeben sei ein Benutzer Alice mit der Email "a@local.local" und dem Benutzernamen "alice"
    Wenn eine Anfrage an /register mit Passwort "Haus1234", Email "a@local.local" und Benutzername "test" gemacht wird
    Dann sollte die Antwort den Status 400 haben
    Und die Fehlermeldung "bereits vergeben" enthalten

  Szenario: Nutzer kann sich danach einloggen
    Wenn eine Anfrage an /register mit Passwort "Haus1234", Email "a@local.local" und Benutzername "test" gemacht wird
    Und eine Anfrage an /login mit dem Benutzernamen "test" und dem Passwort "Haus1234" gemacht wird
    Dann sollten beide Antworten den Status 200 haben
