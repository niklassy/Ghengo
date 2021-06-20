import re
from decimal import Decimal

from django.db.models import IntegerField, FloatField, BooleanField, DecimalField, ManyToManyField, ManyToManyRel, \
    ForeignKey, ManyToOneRel
from spacy.tokens import Token

from django_meta.project import AbstractModelField, ModelInterface
from nlp.generate.argument import Kwarg
from nlp.generate.expression import ModelM2MAddExpression, ModelFactoryExpression, ModelQuerysetFilterExpression
from nlp.generate.variable import Variable
from nlp.generate.warning import GenerationWarning, NO_VALUE_FOUND_CODE, BOOLEAN_NO_SOURCE, VARIABLE_NOT_FOUND, \
    PERMISSION_NOT_FOUND
from nlp.searcher import PermissionSearcher, NoConversionFound
from nlp.vocab import POSITIVE_BOOLEAN_INDICATORS, NEGATIVE_BOOLEAN_INDICATORS
from nlp.utils import get_verb_for_token, token_is_proper_noun, get_all_children, \
    get_noun_chunk_of_token, get_noun_chunks, is_quoted, get_noun_from_chunk, get_proper_noun_from_chunk, \
    token_is_negated


class ExtractionError(Exception):
    """Indicates the the extractor had trouble to get a value."""
    def __init__(self, code):
        self.code = code


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

            if value_str[0] == '<' and value_str[-1] == '>':
                return Variable(value_str, '')

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

    def _extract_value(self):
        return self.get_guessed_python_value(self.source)

    def extract_value(self):
        try:
            return self._extract_value()
        except ExtractionError as e:
            return GenerationWarning.create_for_test_case(e.code, self.test_case)

    def on_handled_by_converter(self, statements):
        pass


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

    def get_guessed_python_value(self, string):
        """Handle variables that were referenced in the past if we dont know the type of field that is used."""
        if isinstance(self.field, AbstractModelField):
            for statement in self.test_case.statements:
                if statement.string_matches_variable(str(string), reference_string=None):
                    return statement.variable.copy()

        return super().get_guessed_python_value(string)

    def _extract_value(self):
        if not isinstance(self.source, Token):
            return super()._extract_value()

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
            raise ExtractionError(NO_VALUE_FOUND_CODE)

        return self.get_guessed_python_value(value)


class NumberModelFieldExtractor(ModelFieldExtractor):
    def _extract_value(self):
        try:
            default_value = super()._extract_value()
        except ExtractionError:
            default_value = None

        if isinstance(self.source, str) and default_value:
            return str(default_value)

        root = self.source
        for child in get_all_children(root):
            if child.is_digit:
                return str(child)

        # check if the default value can be used instead
        if default_value:
            try:
                float(default_value)
                return default_value
            except ValueError:
                pass

        raise ExtractionError(NO_VALUE_FOUND_CODE)


class IntegerModelFieldExtractor(NumberModelFieldExtractor):
    field_classes = (IntegerField,)

    def _extract_value(self):
        return int(super()._extract_value())


class FloatModelFieldExtractor(NumberModelFieldExtractor):
    field_classes = (FloatField,)

    def _extract_value(self):
        return float(super()._extract_value())


class DecimalModelFieldExtractor(NumberModelFieldExtractor):
    field_classes = (DecimalField,)

    def _extract_value(self):
        return Decimal(super()._extract_value())


class BooleanModelFieldExtractor(ModelFieldExtractor):
    field_classes = (BooleanField,)

    def _extract_value(self):
        if isinstance(self.source, str) or self.source is None:
            verb = None
        else:
            verb = get_verb_for_token(self.source)

        if verb is None:
            if self.source is None:
                raise ExtractionError(BOOLEAN_NO_SOURCE)

            return self.source in POSITIVE_BOOLEAN_INDICATORS[self.document.lang_]

        return not token_is_negated(verb) and not token_is_negated(self.source)


class M2MModelFieldExtractor(ModelFieldExtractor):
    field_classes = (ManyToManyField, ManyToManyRel, ManyToOneRel)

    def _extract_value(self):
        return None

    def on_handled_by_converter(self, statements):
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


class ForeignKeyModelFieldExtractor(ModelFieldExtractor):
    field_classes = (ForeignKey,)

    def _extract_value(self):
        value = super()._extract_value()
        related_model = self.field.related_model

        # search for a previous statement where an entry of that model was created and use its variable
        for statement in self.test_case.statements:
            if not isinstance(statement.expression, ModelFactoryExpression) or not statement.variable:
                continue

            expression_model = statement.expression.model_interface.model
            if statement.string_matches_variable(value, related_model.__name__) and expression_model == related_model:
                return statement.variable.copy()

        raise ExtractionError(VARIABLE_NOT_FOUND)


class PermissionsM2MModelFieldExtractor(M2MModelFieldExtractor):
    @classmethod
    def fits_input(cls, field, *args, **kwargs):
        from django.contrib.auth.models import Permission

        return super().fits_input(field, *args, **kwargs) and field.related_model == Permission

    def _extract_value(self):
        return None

    def get_permission_statement(self, searcher_input, statements):
        from django.contrib.auth.models import Permission
        factory_statement = statements[0]

        try:
            permission = PermissionSearcher(searcher_input, self.source.lang_).search(raise_exception=True)
            permission_interface = ModelInterface.create_with_model(Permission)

            permission_query = ModelQuerysetFilterExpression(
                permission_interface,
                [
                    Kwarg('content_type__model', permission.content_type.model),
                    Kwarg('content_type__app_label', permission.content_type.app_label),
                    Kwarg('codename', permission.codename),
                ]
            )
        except NoConversionFound:
            permission_query = GenerationWarning.create_for_test_case(PERMISSION_NOT_FOUND, self.test_case)

        m2m_expression = ModelM2MAddExpression(
            model_instance_variable=factory_statement.variable,
            field=self.field_name,
            add_variable=permission_query,
        )

        return m2m_expression.as_statement()

    def on_handled_by_converter(self, statements):
        factory_statement = statements[0]

        if not factory_statement.variable:
            factory_statement.generate_variable(self.test_case)

        for token in self.source.doc:
            token_str = str(token)[1:-1] if is_quoted(token) else str(token)
            reg_ex = re.compile('([a-z_]+)(\.)([a-z_]+)')

            if reg_ex.match(token_str):
                statement = self.get_permission_statement(token_str.split('.')[1].replace('_', ' '), statements)
                statements.append(statement)
                continue

            token_words = token_str.split()
            if is_quoted(token) and len(token_words) > 1:
                statement = self.get_permission_statement(token_str, statements)
                statements.append(statement)
                continue

        return statements


MODEL_FIELD_EXTRACTORS = [
    IntegerModelFieldExtractor,
    BooleanModelFieldExtractor,
    ForeignKeyModelFieldExtractor,
    FloatModelFieldExtractor,
    DecimalModelFieldExtractor,
    PermissionsM2MModelFieldExtractor,
    M2MModelFieldExtractor,
]


def get_model_field_extractor(field):
    """Returns a model field extractor that fits the given field."""
    for extractor in MODEL_FIELD_EXTRACTORS:
        if extractor.fits_input(field):
            return extractor

    return ModelFieldExtractor
