from rest_framework.fields import Field as RestApiField, BooleanField, IntegerField, FloatField, DecimalField, \
    HiddenField, ModelField
from rest_framework.relations import PrimaryKeyRelatedField, ManyRelatedField

from django_meta.api import AbstractApiFieldAdapter
from nlp.extractor.base import FieldExtractor
from nlp.extractor.exception import ExtractionError
from nlp.extractor.fields_model import get_model_field_extractor
from nlp.extractor.output import BooleanOutput, IntegerOutput, FloatOutput, DecimalOutput, NoneOutput, \
    ModelVariableOutput, ExtractorOutput
from nlp.generate.attribute import Attribute


class ApiModelFieldExtractor(FieldExtractor):
    field_classes = (RestApiField,)
    default_field_class = AbstractApiFieldAdapter

    def __init__(self, test_case, source, field, document):
        super().__init__(test_case, source, field, document)
        self.field_name = self.field.source


class BooleanApiModelFieldExtractor(ApiModelFieldExtractor):
    field_classes = (BooleanField,)
    output_class = BooleanOutput


class IntegerApiModelFieldExtractor(ApiModelFieldExtractor):
    field_classes = (IntegerField,)
    output_class = IntegerOutput


class FloatApiModelFieldExtractor(ApiModelFieldExtractor):
    field_classes = (FloatField,)
    output_class = FloatOutput


class DecimalApiModelFieldExtractor(ApiModelFieldExtractor):
    field_classes = (DecimalField,)
    output_class = DecimalOutput


class NoneApiModelFieldExtractor(ApiModelFieldExtractor):
    """HiddenField should not post data to serializers."""
    field_classes = (HiddenField,)
    output_class = NoneOutput

    @classmethod
    def fits_input(cls, field, *args, **kwargs):
        """All fields that are marked as read_only should not be used in REST API calls."""
        if field.read_only:
            return True

        return super().fits_input(field, *args, **kwargs)


class ModelApiFieldExtractor(ApiModelFieldExtractor):
    field_classes = (ModelField,)
    output_class = None

    def get_output_class(self):
        """
        Since the model field from the rest framework uses this field, we need to find the model field,
        get the extractor for that and use the output class from there.
        """
        if self.field.read_only:
            return NoneOutput

        model_field_extractor = get_model_field_extractor(self.field.model_field)
        return model_field_extractor.output_class


class ForeignKeyApiFieldExtractor(ApiModelFieldExtractor):
    field_classes = (PrimaryKeyRelatedField,)
    output_class = ModelVariableOutput

    def get_output_kwargs(self):
        kwargs = super().get_output_kwargs()
        kwargs['model'] = self.field.get_queryset().model
        kwargs['statements'] = self.test_case.statements
        return kwargs

    def _extract_value(self):
        """We want to handle Variable references but also give the option to simply set values like `1`."""
        try:
            value = super()._extract_value()
        except ExtractionError:
            # if no variable is found that fits, simply try to set a normal value
            default_kwargs = super().get_output_kwargs()
            return ExtractorOutput(**default_kwargs).get_output()
        else:
            # if a variable was found, we want to use the pk of that variable
            return Attribute(value, 'pk')


class Many2ManyApiFieldExtractor(ApiModelFieldExtractor):
    field_classes = (ManyRelatedField,)

    def get_output_class(self):
        # TODO!!!
        pass


class FieldCompatibilityNotes:
    """
    Some notes about some special fields that are interesting/ not implemented:

    ChoiceField:
        ChoiceField should behave like a normal field. We could support to check if the extracted
        value is valid for choices. But that would counteract the thought about new choices being added
        in a given feature. So for now, we leave it as it is.

    FileField:
        For now this is not possible. There needs to be support for a file creation in GIVEN
        statements. If that is given, we can use Variables to reference that file.

        => SimpleUploadedFile("file.mp4", "file_content", content_type="video/mp4")

    ListField, DictField, DefaultSerializer, ListSerializer, ModelSerializer:
        All of these act as nested data. It can be a challenge to explain the data in human language.
        There should be support to create

    JSONField:
        JSONFields can be complex to explain in human language. So for now JSONFields can only add
        data by using quotations: '{"myData": 123}'.

    SerializerMethodField:
        Since we don't know about the type of the SerializerMethodField, we simply have
        to guess the type by the value. So no need to create a special extractor for that.
    """
    pass


API_FIELD_EXTRACTORS = [
    NoneApiModelFieldExtractor,
    BooleanApiModelFieldExtractor,
    IntegerApiModelFieldExtractor,
    FloatApiModelFieldExtractor,
    DecimalApiModelFieldExtractor,
    ModelApiFieldExtractor,
    ForeignKeyApiFieldExtractor,
]


def get_api_model_field_extractor(field):
    """Returns a model field extractor that fits the given field."""
    for extractor in API_FIELD_EXTRACTORS:
        if extractor.fits_input(field):
            return extractor

    return ApiModelFieldExtractor
