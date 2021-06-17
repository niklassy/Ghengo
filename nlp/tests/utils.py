TRANSLATIONS_DE = {
    'nummer': 'number',
    'der nummer': 'number',
    'auftrag': 'order',
    'to-do': 'to do',
    'to do': 'to do',
    'todo': 'to do',
    'lange': 'length',
    'länge': 'length',
    'laenge': 'length',
    'besitzer': 'owner',
    'benutzername': 'username',
    'benutzernamen': 'username',
    'passwort': 'password',
    'besitzerin': 'owner',
    'inventur': 'inventory',
    'system': 'system',
    'dem anderen system': 'the other system',
}


class MockTranslator:
    def __call__(self, text, *args, **kwargs):
        if text.lower() in TRANSLATIONS_DE:
            return TRANSLATIONS_DE[text.lower()]

        return text
