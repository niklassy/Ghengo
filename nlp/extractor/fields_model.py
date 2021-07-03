import re

from django_meta.model import AbstractModelFieldAdapter, ModelAdapter
from nlp.extractor.base import FieldExtractor
from nlp.extractor.output import IntegerOutput, FloatOutput, DecimalOutput, BooleanOutput, NoneOutput, \
    ModelVariableOutput, ManyOutput, StringOutput
from nlp.generate.argument import Kwarg
from nlp.generate.expression import ModelM2MAddExpression, ModelQuerysetFilterExpression
from nlp.generate.warning import GenerationWarning, PERMISSION_NOT_FOUND
from nlp.searcher import PermissionSearcher, NoConversionFound
from nlp.utils import is_quoted
from django.db.models import IntegerField, FloatField, BooleanField, DecimalField, ManyToManyField, ManyToManyRel, \
    ForeignKey, ManyToOneRel, CharField, TextField


class ModelFieldExtractor(FieldExtractor):
    """
    Extracts the value from a token for a given field of a model.
    """
    default_field_class = AbstractModelFieldAdapter

    def __init__(self, test_case, source, model_adapter, field, document):
        super().__init__(test_case=test_case, source=source, document=document, field=field)
        self.model_adapter = model_adapter
        self.field_name = self.field.name


class StringModelFieldExtractor(ModelFieldExtractor):
    field_classes = (CharField, TextField)
    output_class = StringOutput


class IntegerModelFieldExtractor(ModelFieldExtractor):
    field_classes = (IntegerField,)
    output_class = IntegerOutput


class FloatModelFieldExtractor(ModelFieldExtractor):
    field_classes = (FloatField,)
    output_class = FloatOutput


class DecimalModelFieldExtractor(ModelFieldExtractor):
    field_classes = (DecimalField,)
    output_class = DecimalOutput


class BooleanModelFieldExtractor(ModelFieldExtractor):
    field_classes = (BooleanField,)
    output_class = BooleanOutput


class ForeignKeyModelFieldExtractor(ModelFieldExtractor):
    field_classes = (ForeignKey,)
    output_class = ModelVariableOutput

    def get_output_kwargs(self):
        kwargs = super().get_output_kwargs()
        kwargs['statements'] = self.test_case.statements
        kwargs['model'] = self.field.related_model
        return kwargs


class M2MModelFieldExtractor(ModelFieldExtractor):
    field_classes = (ManyToManyField, ManyToManyRel, ManyToOneRel)
    output_class = NoneOutput

    def on_handled_by_converter(self, statements):
        factory_statement = statements[0]

        if not factory_statement.variable:
            factory_statement.generate_variable(self.test_case)

        extractor_output = ManyOutput(
            source=self.source,
            document=self.document,
            test_case=self.test_case,
            child_output_class=ModelVariableOutput,
            child_kwargs={'statements': self.test_case.statements, 'model': self.field.related_model}
        )

        output_list = extractor_output.get_output()

        for variable in output_list:
            m2m_expression = ModelM2MAddExpression(
                model_instance_variable=factory_statement.variable,
                field=self.field_name,
                add_variable=variable,
            )
            statements.append(m2m_expression.as_statement())


class PermissionsM2MModelFieldExtractor(M2MModelFieldExtractor):
    @classmethod
    def fits_input(cls, field, *args, **kwargs):
        from django.contrib.auth.models import Permission

        return super().fits_input(field, *args, **kwargs) and field.related_model == Permission

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
    StringModelFieldExtractor,
]


def get_model_field_extractor(field):
    """Returns a model field extractor that fits the given field."""
    for extractor in MODEL_FIELD_EXTRACTORS:
        if extractor.fits_input(field):
            return extractor

    return ModelFieldExtractor
