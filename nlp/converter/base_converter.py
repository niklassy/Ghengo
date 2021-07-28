from nlp.utils import get_noun_chunks


class Converter(object):
    """
    A converter is a class that converts a given document to code.

    You have to pass a spacy document and it will convert it into code.

    It most likely will do the following:
        1) Find elements/ django classes etc. that match the document
        2) Extract the data to use that class/ element from the text
        3) Create the statements that will become templates sooner or later
    """
    can_use_datatables = False

    def __init__(self, document, related_object, django_project, test_case):
        self.document = document
        self.django_project = django_project
        self.related_object = related_object
        self.language = document.lang_
        self.test_case = test_case
        self._extractors = None
        self._prepared = False

    @property
    def extractors(self):
        if self._extractors is None:
            self._extractors = self.get_extractors()
        return self._extractors

    def get_extractors(self):
        return []

    def get_noun_chunks(self):
        """Returns all the noun chunks from the document."""
        return get_noun_chunks(self.document)

    def convert_to_statements(self):
        """Converts the document into statements."""
        if self._prepared is False:
            self.prepare_converter()
            self._prepared = True

        if not self.related_object.has_datatable or not self.can_use_datatables:
            return self.get_statements_from_extractors(self.extractors)

        return self.get_statements_from_datatable()

    def get_statements_from_datatable(self):
        """If the converter supports special handling for datatables of a Step, overwrite this method."""
        return self.get_statements_from_extractors(self.extractors)

    def prepare_converter(self):
        """Is called before getting the statements from the extractors."""
        pass

    def get_document_compatibility(self):
        """
        Returns the compatibility of a document. This represents how well this converter fits the given document.

        Returns:
            value from 0-1
        """
        return 1

    def add_extractor_warnings_to_test_case(self, extractor):
        """Adds any warnings that the given extractor generated to the test case."""
        if extractor.generates_warning:
            warnings = extractor.get_generated_warnings()

            for warning in warnings:
                self.test_case.test_suite.warning_collection.add_warning(warning.code)

    def handle_extractor(self, extractor, statements):
        """Does everything that is needed when an extractor is called."""
        # some extractors add more statements, so add them here if needed
        extractor.on_handled_by_converter(statements)
        self.add_extractor_warnings_to_test_case(extractor)

    def prepare_statements(self, statements):
        """Can be used to do something before the extractors are handled."""
        return statements

    def get_statements_from_extractors(self, extractors):
        """Function to return statements based on extractors."""
        statements = []
        prepared_statements = self.prepare_statements(statements)

        # go through each extractor and append its kwargs to the factory kwargs
        for extractor in extractors:
            self.handle_extractor(extractor, prepared_statements)

        return prepared_statements
