from decimal import Decimal

from django.db.models import IntegerField, FloatField, BooleanField, DecimalField, ManyToManyField, ManyToManyRel, \
    ForeignKey, ManyToOneRel

from nlp.generate.expression import ModelM2MAddExpression, ModelFactoryExpression
from nlp.generate.variable import Variable
from nlp.generate.warning import GenerationWarning, NO_VALUE_FOUND_CODE, BOOLEAN_NO_SOURCE
from nlp.vocab import POSITIVE_BOOLEAN_INDICATORS, NEGATIVE_BOOLEAN_INDICATORS
from nlp.utils import get_verb_for_token, token_is_proper_noun, get_all_children, \
    get_noun_chunk_of_token, get_noun_chunks, is_quoted, get_noun_from_chunk, get_proper_noun_from_chunk, \
    token_is_negated


class Extractor(object):
    """
    Extractors turn Tokens and strings into Python values that can be used in the generate part.
    """
    def __init__(self, test_case, source, document):
        self.test_case = test_case
        self.source = source
        self.document = document

    @classmethod
    def fits_input(cls, *args, **kwargs):
        return False

    def get_guessed_python_value(self, string):
        """
        Uses a string as an input to get a python value that may fit that string.
        """
        value_str = str(string)

        # remove any quotations
        if is_quoted(value_str):
            value_str = value_str[1:-1]

        # try to get int
        try:
            return int(value_str)
        except ValueError:
            pass

        # try float value
        try:
            return float(value_str)
        except ValueError:
            pass

        # check if the value may be a boolean
        bool_pos = POSITIVE_BOOLEAN_INDICATORS[self.document.lang_]
        bool_neg = NEGATIVE_BOOLEAN_INDICATORS[self.document.lang_]
        if value_str in bool_pos or value_str in bool_neg:
            return value_str in bool_pos

        # just return the value
        return value_str

    def extract_value(self):
        return self.get_guessed_python_value(self.source)

    def get_statements(self, statements):
        return statements


class ModelFieldExtractor(Extractor):
    """
    Extracts the value from a token for a given field of a model.
    """
    field_classes = ()

    def __init__(self, test_case, source, model_interface, field, document):
        super().__init__(test_case, source, document)
        self.model_interface = model_interface
        self.field = field
        self.field_name = field.name

    @classmethod
    def fits_input(cls, field, *args, **kwargs):
        return isinstance(field, cls.field_classes)

    def extract_value(self):
        if isinstance(self.source, str):
            return super().extract_value()

        # if the token is an adjective or verb, it will most likely be a boolean field
        if self.source.pos_ == 'ADJ' or self.source.pos_ == 'VERB':
            return not token_is_negated(self.source)

        document = self.source.doc
        noun_chunks = get_noun_chunks(document)
        chunk = get_noun_chunk_of_token(self.source, self.source.doc)
        chunk_index = noun_chunks.index(chunk)
        value = None

        try:
            next_token = document[self.source.i + 1]
        except IndexError:
            next_token = None

        # check if any children is a digit or a proper noun, if yes they are the value
        for child in self.source.children:
            if child.is_digit or token_is_proper_noun(child):
                value = child
                break

        # as an alternative, if the next token is in quotes it should be the value
        if value is None and is_quoted(next_token):
            value = next_token

        # if still nothing is found, the value might be in a previous noun chunk
        try:
            previous_chunk = noun_chunks[chunk_index - 1]
            previous_propn = get_proper_noun_from_chunk(previous_chunk)
            if value is None and get_noun_from_chunk(previous_chunk) is None and previous_propn:
                value = previous_propn
        except IndexError:
            pass

        if value is None:
            return GenerationWarning.create_for_test_case(NO_VALUE_FOUND_CODE, self.test_case)

        return super().get_guessed_python_value(value)


class NumberModelFieldExtractor(ModelFieldExtractor):
    def extract_value(self):
        default_value = super().extract_value()

        if not self.source:
            return str(default_value)

        root = self.source
        for child in get_all_children(root):
            if child.is_digit:
                return str(child)

        raise ValueError('There was not a number found for field {}'.format(self.field_name))


class IntegerModelFieldExtractor(NumberModelFieldExtractor):
    field_classes = (IntegerField,)

    def extract_value(self):
        return int(super().extract_value())


class FloatModelFieldExtractor(NumberModelFieldExtractor):
    field_classes = (FloatField,)

    def extract_value(self):
        return float(super().extract_value())


class DecimalModelFieldExtractor(NumberModelFieldExtractor):
    field_classes = (DecimalField,)

    def extract_value(self):
        return Decimal(super().extract_value())


class BooleanModelFieldExtractor(ModelFieldExtractor):
    field_classes = (BooleanField,)

    def extract_value(self):
        if isinstance(self.source, str):
            verb = None
        else:
            verb = get_verb_for_token(self.source)

        if verb is None:
            if self.source is None:
                return GenerationWarning.create_for_test_case(BOOLEAN_NO_SOURCE, self.test_case)

            return self.source in POSITIVE_BOOLEAN_INDICATORS[self.document.lang_]

        return not token_is_negated(verb) and not token_is_negated(self.source)


class M2MModelFieldExtractor(ModelFieldExtractor):
    field_classes = (ManyToManyField, ManyToManyRel, ManyToOneRel)

    def extract_value(self):
        return None

    def get_statements(self, statements):
        factory_statement = statements[0]

        if not factory_statement.variable:
            factory_statement.generate_variable(self.test_case)

        for child in get_all_children(self.source):
            if not child:
                continue

            if child.is_digit or token_is_proper_noun(child):
                related_model = self.field.related_model
                related_name = related_model.__name__
                variable = Variable(name_predetermined=str(child), reference_string=related_name)

                for statement in self.test_case.statements:
                    expression = statement.expression
                    if not isinstance(expression, ModelFactoryExpression):
                        continue

                    # check if the value can become the variable and if the expression has the same model
                    expression_model = expression.model_interface.model
                    variable_matches = statement.string_matches_variable(str(child), related_name)
                    if variable_matches and expression_model == related_model:
                        variable = statement.variable.copy()
                        break

                m2m_expression = ModelM2MAddExpression(
                    model_instance_variable=factory_statement.variable,
                    field=self.field_name,
                    add_variable=variable
                )
                statements.append(m2m_expression.as_statement())

        return statements


class ForeignKeyModelFieldExtractor(ModelFieldExtractor):
    field_classes = (ForeignKey,)

    def extract_value(self):
        value = super().extract_value()
        related_model = self.field.related_model

        # search for a previous statement where an entry of that model was created and use its variable
        for statement in self.test_case.statements:
            if not isinstance(statement.expression, ModelFactoryExpression) or not statement.variable:
                continue

            expression_model = statement.expression.model_interface.model
            if statement.string_matches_variable(value, related_model.__name__) and expression_model == related_model:
                return statement.variable.copy()

        return value


MODEL_FIELD_EXTRACTORS = [
    IntegerModelFieldExtractor,
    BooleanModelFieldExtractor,
    ForeignKeyModelFieldExtractor,
    FloatModelFieldExtractor,
    DecimalModelFieldExtractor,
    M2MModelFieldExtractor,
]


def get_model_field_extractor(field):
    """Returns a model field extractor that fits the given field."""
    for extractor in MODEL_FIELD_EXTRACTORS:
        if extractor.fits_input(field):
            return extractor

    return ModelFieldExtractor


# ========= OLD IMPLEMENTATION EXTRACTOR LOGIC ==========

"""
@property
def extractors(self):
    if self._extractors is None:
        fields = []
        handled_non_stop = []
        non_stop_tokens = get_non_stop_tokens(self.document)

        # the first noun_chunk holds the model, so skip it
        unhandled_noun_chunks = self.get_noun_chunks()[1:].copy()
        unhandled_propn_chunk = None

        model_noun_chunk = get_noun_chunk_of_token(self.model_token, self.document)

        # go through each non stop token
        for non_stop_token in non_stop_tokens:
            # if that token is part of the model definition, skip it
            if non_stop_token.i < model_noun_chunk.end or self.variable_token == non_stop_token:
                handled_non_stop.append(non_stop_token)
                continue

            # get the head of the non_stop_token
            head = non_stop_token.head

            # extract the current noun_chunk
            try:
                noun_chunk = unhandled_noun_chunks[0]
            except IndexError:
                noun_chunk = []

            # ========== CLEAN NOUN_CHUNKS ==========
            if non_stop_token in noun_chunk:
                # if the current token is the last one in the chunk, mark the chunk as handled
                if non_stop_token == noun_chunk[-1]:
                    unhandled_noun_chunks.remove(noun_chunk)

                # if the root of the chunk is a proper noun (normally a noun), it needs to be handled later
                if get_noun_from_chunk(noun_chunk) is None and get_proper_noun_from_chunk(noun_chunk):
                    unhandled_propn_chunk = noun_chunk
                    continue
            # if the last token of that chunk is not present in the non stop tokens, mark the chunk as handled
            elif bool(noun_chunk) and noun_chunk[-1] not in non_stop_tokens:
                unhandled_noun_chunks.remove(noun_chunk)

            # if the token was already handled, continue
            if non_stop_token in handled_non_stop:
                continue

            # ========== GET VALUE AND SOURCE ===========
            # if the head is in the non stop tokens and not already handled, it is considered the field
            # and the token is the value
            noun_or_verb_head = token_is_noun(head) or token_is_verb(head, include_aux=False)
            if head in non_stop_tokens and head not in model_noun_chunk and noun_or_verb_head:
                field_token = head
                field_value_token = non_stop_token

            # if there was an unhandled proper noun, the token is the field and the value is the root of the
            # unhandled proper noun
            elif unhandled_propn_chunk:
                field_token = non_stop_token
                field_value_token = get_proper_noun_from_chunk(unhandled_propn_chunk)

            # if the root of the current noun chunk is a noun, that noun is the field; the value is the proper
            # noun of of that chunk
            elif bool(noun_chunk) and token_is_noun(noun_chunk.root):
                field_token = noun_chunk.root
                field_value_token = get_proper_noun_of_chunk(field_token, noun_chunk)

            # above we checked the head of the non stop token, check the token itself here too
            elif token_is_noun(non_stop_token) or token_is_verb(non_stop_token, include_aux=False):
                field_token = non_stop_token
                field_value_token = get_proper_noun_of_chunk(field_token, noun_chunk)

            else:
                continue

            # ========== GET FIELD ==========
            noun_chunk = get_noun_chunk_of_token(field_token, self.document)
            field = self._search_for_field(span=noun_chunk, token=field_token)

            if field is None:
                continue

            handled_non_stop.append(head)
            handled_non_stop.append(non_stop_token)
            unhandled_propn_chunk = None

            if field in [f for f, _, _ in fields]:
                continue

            fields.append((field, field_token, field_value_token))

        # ========== BUILD EXTRACTORS ==========
        extractors = []
        for field, field_token, value_token in fields:
            extractors.append(
                ModelFieldExtractor(self.test_case, value_token, field_token, self.model_interface, field))

        self._extractors = extractors
    return self._extractors
"""
