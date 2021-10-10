class Languages:
    """
    Strings that represent all languages that this application supports.
    """
    DE = 'de'
    EN = 'en'

    @classmethod
    def get_supported_languages(cls):
        return [cls.DE, cls.EN]


class GenerationType:
    PY_TEST = 'py_test'
