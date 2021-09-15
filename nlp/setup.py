import spacy
from spacy import Language
from spacy.matcher import Matcher

from core.constants import Languages
from core.exception import LanguageNotSupported


class CacheNlp:
    """
    Over the course of the lifetime of the application nlp is called very often. Especially with the same text
    again and again in order to find special tokens and so on. In order to reduce the calls to the NLP, we cache
    the return values for each text and use that in future calls.
    """
    def __init__(self, name):
        self.nlp = spacy.load(name)
        self.cache = {}

    def get_document(self, text):
        """Get the document from the cache."""
        return self.cache[text].copy()

    def cache_document(self, text):
        """Cache the document for a given text."""
        self.cache[text] = self.nlp(text)

    def __call__(self, text):
        if text not in self.cache:
            self.cache_document(text)

        return self.get_document(text)


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
            self._de_nlp = CacheNlp('de_core_news_lg')
            self.add_quotation_matcher(self._de_nlp.nlp)
            print('German nlp done!')
        return self._de_nlp

    @property
    def en_nlp(self):
        if self._en_nlp is None:
            print('Setting up english nlp...')
            self._en_nlp = CacheNlp('en_core_web_lg')
            self.add_quotation_matcher(self._en_nlp.nlp)
            print('English nlp done!')
        return self._en_nlp

    def for_language(self, language):
        if language == Languages.DE:
            return self.de_nlp

        if language == Languages.EN:
            return self.en_nlp

        raise LanguageNotSupported()

    def setup_languages(self, languages):
        """Setups NLP for all the given languages."""
        for language in languages:
            self.for_language(language)


Nlp = _Nlp()

b = Nlp.for_language('de')('Gegeben sei ein abgeschlossener Auftrag mit der Nummer 3.')
c = 1
