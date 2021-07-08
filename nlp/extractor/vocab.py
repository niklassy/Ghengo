POSITIVE_BOOLEAN_INDICATORS_BASE = ['1', 'True', 'true']

POSITIVE_BOOLEAN_INDICATORS = {
    'de': POSITIVE_BOOLEAN_INDICATORS_BASE + ['wahr', 'Wahr', 'Richtig', 'richtig', 'Ja', 'ja'],
    'en': POSITIVE_BOOLEAN_INDICATORS_BASE + ['Correct', 'correct', 'Yes', 'yes'],
}

NEGATIVE_BOOLEAN_INDICATORS_BASE = ['0', 'False', 'false']

NEGATIVE_BOOLEAN_INDICATORS = {
    'de': NEGATIVE_BOOLEAN_INDICATORS_BASE + ['Falsch', 'falsch', 'Nein', 'nein'],
    'en': NEGATIVE_BOOLEAN_INDICATORS_BASE + ['Incorrect', 'incorrect', 'No', 'no'],
}
