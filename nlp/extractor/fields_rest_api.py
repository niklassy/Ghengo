from rest_framework.fields import Field as RestApiField, BooleanField, IntegerField, FloatField, DecimalField, \
    ReadOnlyField, HiddenField, ModelField

from django_meta.api import AbstractApiFieldAdapter
from nlp.extractor.base import FieldExtractor
from nlp.extractor.fields_model import get_model_field_extractor
from nlp.extractor.output import BooleanOutput, IntegerOutput, FloatOutput, DecimalOutput, NoneOutput


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
    """ReadOnly and HiddenField should not post data to serializers."""
    field_classes = (ReadOnlyField, HiddenField)
    output_class = NoneOutput


class ModelApiFieldExtractor(ApiModelFieldExtractor):
    field_classes = (ModelField,)
    output_class = None

    def get_output_class(self):
        """
        Since the model field from the rest framework uses this field, we need to find the model field,
        get the extractor for that and use the output class from there.
        """
        model_field_extractor = get_model_field_extractor(self.field.model_field)
        return model_field_extractor.output_class


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

    ListField, DictField:
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
    BooleanApiModelFieldExtractor,
    IntegerApiModelFieldExtractor,
    FloatApiModelFieldExtractor,
    DecimalApiModelFieldExtractor,
    NoneApiModelFieldExtractor,
    ModelApiFieldExtractor,
]


def get_api_model_field_extractor(field):
    """Returns a model field extractor that fits the given field."""
    for extractor in API_FIELD_EXTRACTORS:
        if extractor.fits_input(field):
            return extractor

    return ApiModelFieldExtractor
