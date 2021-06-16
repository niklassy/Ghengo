from nlp.searcher import Searcher, NoConversionFound


def test_searcher_search_no_results():
    """Try to search when there are no possible results."""
    searcher = Searcher('Auftrag', 'de')
    # by default the input text should be returned
    assert searcher.search() == 'Auftrag'
    try:
        searcher.search(raise_exception=True)
        assert False
    except NoConversionFound:
        pass


def test_searcher_search_with_results():
    """Check that the result is chosen with the highest similarity."""
    class CustomSearcher(Searcher):
        def get_possible_results(self, *args, **kwargs):
            return [1, 0, 6, 4, 2]

        def get_comparisons(self, integer):
            return [(integer, None)]

        def get_similarity(self, input_doc, target_doc):
            """Simply return the input_doc, which will be an integer."""
            return input_doc

    searcher = CustomSearcher('Auftrag', 'de')
    assert searcher.search() == 6
