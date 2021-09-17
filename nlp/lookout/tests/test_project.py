from core.constants import Languages
from nlp.lookout.base import Lookout


def test_searcher_search_with_results():
    """Check that the result is chosen with the highest similarity."""
    class Custom6Searcher(Lookout):
        def get_output_objects(self, *args, **kwargs):
            return [1, 0, 6, 4, 2]

        def get_compare_variations(self, integer, keyword):
            return [(integer, None)]

        def get_keywords(self, integer):
            return [integer]

        def get_similarity(self, input_doc, target_doc):
            """Simply return the input_doc, which will be an integer."""
            return 1 if input_doc == 6 else 0

        def get_fallback(self):
            return None

    searcher = Custom6Searcher('Auftrag', Languages.DE)
    assert searcher.locate(None) == 6
