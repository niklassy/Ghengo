from Levenshtein import ratio


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
    """Returns the similarity by checking if some words are inside the strings of the other."""
    def get_similarity(self):
        str_input_1 = str(self.input_1)
        str_input_2 = str(self.input_2)

        if str_input_1.lower() == str_input_2.lower():
            return 1

        if len(str_input_1) == len(str_input_2):
            return 0

        if len(str_input_1) > len(str_input_2):
            shorter_string = str_input_2
            longer_string = str_input_1
        else:
            shorter_string = str_input_1
            longer_string = str_input_2

        if shorter_string in longer_string:
            return 0.8

        words = shorter_string.split()
        hits = [word for word in words if word in longer_string]

        if len(hits) > 0:
            return float(len(hits) / len(words))

        return 0


class LevenshteinSimilarity(Similarity):
    def get_similarity(self):
        return ratio(str(self.input_1), str(self.input_2))
