import spacy
from spacy import Language
from spacy.matcher import Matcher


class _Nlp(object):
    def __init__(self):
        self._de_nlp = None
        self._en_nlp = None

    @classmethod
    def add_quotation_matcher(cls, nlp):
        matcher = Matcher(nlp.vocab)
        matcher.add(
            'QUOTED',
            [
                [
                    {'ORTH': {'IN': ['"']}},
                    {'OP': '+', 'LENGTH': {'>': 0}},
                    {'ORTH': {'IN': ['"']}}
                ],
                [
                    {'ORTH': {'IN': ["'"]}},
                    {'OP': '+', 'LENGTH': {'>': 0}},
                    {'ORTH': {'IN': ["'"]}}
                ],
            ]
        )

        @Language.component("QUOTE_MERGER")
        def quote_merger(doc):
            # this will be called on the Doc object in the pipeline
            matched_spans = []
            matches = matcher(doc)
            for match_id, start, end in matches:
                span = doc[start:end]
                matched_spans.append(span)

            matched_spans.reverse()
            clean_matched_spans = []
            for i, span in enumerate(matched_spans):
                span_str = str(span)

                # if there are more than 2 of the quotation, skip it
                quotation_character = span_str[0]
                if span_str.count(quotation_character) > 2:
                    continue

                # if the span is contained in another cleaned one, skip it
                if any([span.start >= s.start and span.end <= s.end for s in clean_matched_spans]):
                    continue

                # check if the span starts with a token that was already handled
                if any([s.start <= span.start <= s.end or s.start <= span.end <= s.end for s in clean_matched_spans]):
                    continue

                clean_matched_spans.append(span)

            for index, span in enumerate(clean_matched_spans):
                with doc.retokenize() as retokenizer:
                    # merge into one token after collecting all matches
                    retokenizer.merge(span)

            return doc

        nlp.add_pipe('QUOTE_MERGER', first=True)

    @property
    def de_nlp(self):
        if self._de_nlp is None:
            print('Setting up german nlp...')
            self._de_nlp = spacy.load('de_core_news_lg')
            self.add_quotation_matcher(self._de_nlp)
            print('German nlp done!')
        return self._de_nlp

    @property
    def en_nlp(self):
        if self._en_nlp is None:
            print('Setting up english nlp...')
            self._en_nlp = spacy.load('en_core_web_lg')
            self.add_quotation_matcher(self._en_nlp)
            print('English nlp done!')
        return self._en_nlp

    def for_language(self, language):
        if language == 'de':
            return self.de_nlp

        if language == 'en':
            return self.en_nlp

        raise ValueError('Language is not supported yet.')


Nlp = _Nlp()
