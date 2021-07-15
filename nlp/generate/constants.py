class CompareChar:
    EQUAL = '=='
    SMALLER = '<'
    SMALLER_EQUAL = '<='
    GREATER = '>'
    GREATER_EQUAL = '>='

    @classmethod
    def get_all(cls):
        return [cls.EQUAL, cls.SMALLER, cls.SMALLER_EQUAL, cls.GREATER, cls.GREATER_EQUAL]
