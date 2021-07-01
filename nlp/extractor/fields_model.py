import re
from decimal import Decimal

from spacy.tokens.token import Token

from django_meta.model import AbstractModelFieldAdapter, ModelAdapter
from nlp.extractor.base import Extractor
from nlp.extractor.exception import ExtractionError
from nlp.extractor.utils import extract_boolean
from nlp.generate.argument import Kwarg
from nlp.generate.expression import ModelFactoryExpression, ModelM2MAddExpression, ModelQuerysetFilterExpression
from nlp.generate.variable import Variable
from nlp.generate.warning import NO_VALUE_FOUND_CODE, VARIABLE_NOT_FOUND, GenerationWarning, PERMISSION_NOT_FOUND
from nlp.searcher import PermissionSearcher, NoConversionFound
from nlp.utils import token_is_negated, get_noun_chunks, get_noun_chunk_of_token, token_is_proper_noun, is_quoted, \
    get_proper_noun_from_chunk, get_noun_from_chunk, get_all_children
from django.db.models import IntegerField, FloatField, BooleanField, DecimalField, ManyToManyField, ManyToManyRel, \
    ForeignKey, ManyToOneRel


class ModelFieldExtractor(Extractor):
    """
    Extracts the value from a token for a given field of a model.
    """
    field_classes = ()

    def __init__(self, test_case, source, model_adapter, field, document):
        super().__init__(test_case, source, document)
        self.model_adapter = model_adapter
        self.field = field

        try:
            self.field_name = field.name
        except AttributeError:
            self.field_name = None

    @classmethod
    def fits_input(cls, field, *args, **kwargs):
        return isinstance(field, cls.field_classes)

    def get_guessed_python_value(self, string):
        """Handle variables that were referenced in the past if we dont know the type of field that is used."""
        if isinstance(self.field, AbstractModelFieldAdapter):
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
        return extract_boolean(self.source, self.document)


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
                    expression_model = expression.model_adapter.model
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

            expression_model = statement.expression.model_adapter.model
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
            permission_adapter = ModelAdapter.create_with_model(Permission)

            permission_query = ModelQuerysetFilterExpression(
                permission_adapter,
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
