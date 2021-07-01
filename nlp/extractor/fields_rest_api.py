from rest_framework.fields import Field as RestApiField, BooleanField

from django_meta.api import AbstractApiFieldAdapter
from nlp.extractor.base import FieldExtractor
from nlp.extractor.exception import ExtractionError
from nlp.extractor.output import VariableOutput, BooleanOutput


class ApiModelFieldExtractor(FieldExtractor):
    field_classes = (RestApiField,)
    default_field_class = AbstractApiFieldAdapter

    def __init__(self, test_case, source, field, document):
        super().__init__(test_case, source, field, document)
        self.field_name = self.field.source

    def _extract_value(self):
        extracted_value = super()._extract_value()

        # if the field does not exist yet, see if there is any variable in the test case that matches the variable.
        # If yes, we assume that the variable is meant
        if isinstance(self.field, AbstractApiFieldAdapter):
            variable_output = VariableOutput(self.source, self.document, self.test_case.statements)

            try:
                return variable_output.get_output()
            except ExtractionError:
                pass

        return extracted_value


class BooleanApiModelFieldExtractor(ApiModelFieldExtractor):
    field_classes = (BooleanField,)
    output_class = BooleanOutput


API_FIELD_EXTRACTORS = [
    BooleanApiModelFieldExtractor,
]


def get_api_model_field_extractor(field):
    """Returns a model field extractor that fits the given field."""
    for extractor in API_FIELD_EXTRACTORS:
        if extractor.fits_input(field):
            return extractor

    return ApiModelFieldExtractor
