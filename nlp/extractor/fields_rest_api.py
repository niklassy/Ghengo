from rest_framework.fields import Field as RestApiField, BooleanField

from django_meta.api import AbstractApiFieldAdapter
from nlp.extractor.fields_model import ModelFieldExtractor
from nlp.extractor.utils import extract_boolean


class ApiModelFieldExtractor(ModelFieldExtractor):
    field_classes = (RestApiField,)

    def __init__(self, test_case, source, model_adapter, field, document):
        super().__init__(test_case, source, model_adapter, field, document)
        self.field_name = field.source

    def get_guessed_python_value(self, string):
        """Handle variables that were referenced in the past if we dont know the type of field that is used."""
        if isinstance(self.field, AbstractApiFieldAdapter):
            for statement in self.test_case.statements:
                if statement.string_matches_variable(str(string), reference_string=None):
                    return statement.variable.copy()

        return super().get_guessed_python_value(string)


class BooleanApiModelFieldExtractor(ApiModelFieldExtractor):
    field_classes = (BooleanField,)

    def _extract_value(self):
        return extract_boolean(self.source, self.document)


API_FIELD_EXTRACTORS = [
    BooleanApiModelFieldExtractor,
]


def get_api_model_field_extractor(field):
    """Returns a model field extractor that fits the given field."""
    for extractor in API_FIELD_EXTRACTORS:
        if extractor.fits_input(field):
            return extractor

    return ApiModelFieldExtractor
