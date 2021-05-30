# language: de
Funktionalität: Freundschaften

  Grundlage:
    Gegeben sei ein Benutzer Alice mit dem Benutzernamen "alice"
    Und ein Benutzer Bob mit dem Benutzernamen "bob"
    Und ein Benutzer Cedric mit dem Benutzernamen "ced"

  Szenario: Nicht eingeloggt
    Wenn ein unbekannter Nutzer eine Anfrage an /befriend mit der Id von Bob schickt
    Dann sollte die Antwort den Status 400 haben

  Szenario: Mögliche Freunde auflisten
    Wenn Alice eine Anfrage an /accounts/ macht
    Dann sollte in der Liste Bob enthalten sein

  Szenario: Freundschaftsanfrage schicken
    Wenn Alice eine Anfrage an /befriend/request/ mit der Id von Bob schickt
    Dann sollte Bob eine Freundschaftsanfrage haben

  Szenario: Freundschaftsanfrage annehmen
    Gegeben sei eine Freunschaftsanfrage von Alice an Bob
    Wenn Bob eine Anfrage an /befriend/accept/ schickt
    Dann sollte Bob Alice als Freund haben
    Und Alice sollte Bob als Freund haben
