from core.constants import Languages

POSITIVE_BOOLEAN_INDICATORS_BASE = ['1', 'True', 'true']

POSITIVE_BOOLEAN_INDICATORS = {
    Languages.DE: POSITIVE_BOOLEAN_INDICATORS_BASE + ['wahr', 'Wahr', 'Richtig', 'richtig', 'Ja', 'ja'],
    Languages.EN: POSITIVE_BOOLEAN_INDICATORS_BASE + ['Correct', 'correct', 'Yes', 'yes'],
}

NEGATIVE_BOOLEAN_INDICATORS_BASE = ['0', 'False', 'false']

NEGATIVE_BOOLEAN_INDICATORS = {
    Languages.DE: NEGATIVE_BOOLEAN_INDICATORS_BASE + ['Falsch', 'falsch', 'Nein', 'nein'],
    Languages.EN: NEGATIVE_BOOLEAN_INDICATORS_BASE + ['Incorrect', 'incorrect', 'No', 'no'],
}
