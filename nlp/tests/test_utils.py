from nlp.utils import token_is_verb, token_is_proper_noun, token_is_noun, get_non_stop_tokens, get_noun_chunks, \
    token_references, is_proper_noun_of, get_verb_for_token, get_proper_noun_of_chunk, get_noun_chunk_of_token, \
    get_all_children


class MockToken:
    def __init__(self, **kwargs):
        for key in kwargs:
            setattr(self, key, kwargs[key])


class MockDocument:
    def __init__(self, tokens, **kwargs):
        self.tokens = tokens
        for key in kwargs:
            setattr(self, key, kwargs[key])
        self._n = None

    def __iter__(self):
        self._n = 0
        return self

    def __next__(self):
        if self._n >= len(self.tokens):
            raise StopIteration
        output = self.tokens[self._n]
        self._n += 1
        return output


def test_token_is_verb():
    """Checks if token_is_verb uses pos_ correctly."""
    assert token_is_verb(MockToken(pos_='VERB')) is True
    assert token_is_verb(MockToken(pos_='NOUN')) is False
    assert token_is_verb(MockToken(pos_='AUX'), include_aux=False) is False
    assert token_is_verb(MockToken(pos_='AUX'), include_aux=True) is True


def test_token_is_proper_noun():
    """Checks if token_is_proper_noun uses pos_ correctly."""
    assert token_is_proper_noun(MockToken(pos_='PROPN')) is True
    assert token_is_proper_noun(MockToken(pos_='NOUN')) is False
    assert token_is_proper_noun(MockToken(pos_='asdasdasd')) is False


def test_token_is_noun():
    """Checks if token_is_noun uses pos_ correctly."""
    assert token_is_noun(MockToken(pos_='NOUN')) is True
    assert token_is_noun(MockToken(pos_='asasdasd')) is False
    assert token_is_noun(MockToken(pos_='VERB')) is False


def test_get_non_stop_tokens():
    """Check if get_non_stop_tokens returns only tokens that are marked as `is_stop=False`"""
    tokens = [MockToken(is_stop=True), MockToken(is_stop=False)]
    doc = MockDocument(tokens)
    assert len(get_non_stop_tokens(doc)) == 1
    assert get_non_stop_tokens(doc)[0] == tokens[1]


def test_get_noun_chunks():
    """Check if get_noun_chunks extracts the noun chunks from the document."""
    assert get_noun_chunks(MockDocument([], noun_chunks=[123, 234])) == [123, 234]
    assert get_noun_chunks(MockDocument([], noun_chunks=[])) == []
    assert get_noun_chunks(MockDocument([], noun_chunks=['123'])) == ['123']


def test_token_references():
    """Check if token_references uses the head attribute from spacy."""
    token = MockToken(head=None)
    token_child = MockToken(head=token)
    assert token_references(token_child, token) is True
    assert token_references(token, token_child) is False
    assert token_references(token_child, token_child) is False
    assert token_references(MockToken(head=None), token_child) is False


def test_is_proper_noun_of():
    """Check if is_proper_noun_of determines if a token references another and is a proper noun."""
    token = MockToken(head=None)
    token_child = MockToken(head=token, pos_='PROPN')
    assert is_proper_noun_of(token_child, token) is True
    assert is_proper_noun_of(MockToken(head=token, pos_='NOUN'), token) is False
    assert is_proper_noun_of(MockToken(head=token_child, pos_='PROPN'), token) is False


def test_get_verb_for_token():
    """Check that searching for a verb works."""
    token = MockToken(head=None, pos_='VERB')
    token_child = MockToken(head=token, pos_='PROPN')
    assert get_verb_for_token(token_child) == token
    assert get_verb_for_token(token) == token
    assert get_verb_for_token(MockToken(head=None, pos_=None)) is None


def test_get_proper_noun_of_chunk():
    """Check if get_proper_noun_of_chunk searches for the correct token."""
    head = MockToken(pos_='NOUN')
    tokens = [MockToken(head=head, pos_='NOUN'), MockToken(head=None, pos_='VERB'), MockToken(head=head, pos_='PROPN')]
    doc = MockDocument(tokens)
    assert get_proper_noun_of_chunk(head, doc) == tokens[2]


def test_get_noun_chunk_of_token():
    """Check if searching for a noun chunk works just as expected."""
    token = MockToken()
    noun_chunks = [
        MockDocument([token, MockToken()]),
        MockDocument([MockToken()]),
        MockDocument([MockToken(), MockToken(), MockToken()])
    ]
    doc = MockDocument([], noun_chunks=noun_chunks)
    assert get_noun_chunk_of_token(token, doc) == noun_chunks[0]


def test_get_all_children():
    """Check if get_all_children returns all children and all sub-children."""
    t_3 = MockToken(children=[])
    t_2 = MockToken(children=[t_3])
    t_1 = MockToken(children=[t_2, MockToken(children=[])])
    assert len(get_all_children(t_1)) == 3
