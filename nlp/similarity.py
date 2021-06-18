class Similarity(object):
    def __init__(self, input_1, input_2):
        self.input_1 = input_1
        self.input_2 = input_2

    def get_similarity(self):
        raise NotImplementedError()


class CosineSimilarity(Similarity):
    def get_similarity(self):
        """It is assumed that the input is from spacy. Spacy implements the Cosine distance for similarity."""
        if not self.input_1.vector_norm or not self.input_2.vector_norm:
            return 0

        return self.input_1.similarity(self.input_2)


class ContainsSimilarity(Similarity):
    def get_similarity(self):
        if str(self.input_1) == str(self.input_2):
            return 1

        if str(self.input_1) in str(self.input_2) or str(self.input_2) in str(self.input_1):
            return 0.8

        return 0
