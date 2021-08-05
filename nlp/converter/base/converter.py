from nlp.converter.wrapper import ConverterInitArgumentWrapper
from nlp.generate.suite import TestCaseBase
from nlp.searcher import NoConversionFound
from nlp.utils import get_noun_chunks, get_non_stop_tokens, get_noun_chunk_of_token, token_is_verb, NoToken


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
        self.test_case: TestCaseBase = test_case
        self._extractors = None
        self._prepared = False

        self._creating_statements = False

    class ExtractorReturnedNone(Exception):
        pass

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

    def extract_and_handle_output(self, extractor):
        """
        This function is a wrapper around the extract_value function. It is used to perform tasks before returning the
        extracted value.
        """
        assert self._creating_statements, 'You should only call this function in `handle_extractor`, ' \
                                          '`prepare_statements` and `finish_statements`. If you want to get the ' \
                                          'value from an extractor, call `extract_value` instead.'

        self.add_extractor_warnings_to_test_case(extractor)
        extracted_value = extractor.extract_value()

        if extracted_value is None:
            raise self.ExtractorReturnedNone()

        return extracted_value

    def handle_extractor(self, extractor, statements):
        """Does everything that is needed when an extractor is called."""
        # some extractors add more statements, so add them here if needed
        extractor.on_handled_by_converter(statements)

    def prepare_statements(self, statements):
        """Can be used to do something before the extractors are handled."""
        return statements

    def finish_statements(self, statements):
        """Can be used to do something after the extractors are handled."""
        return statements

    def get_statements_from_extractors(self, extractors):
        """Function to return statements based on extractors."""
        statements = []
        self._creating_statements = True

        try:
            prepared_statements = self.prepare_statements(statements)
        except self.ExtractorReturnedNone:
            prepared_statements = []

        # go through each extractor and append its kwargs to the factory kwargs
        for extractor in extractors:
            try:
                self.handle_extractor(extractor, prepared_statements)
            except self.ExtractorReturnedNone:
                continue

        try:
            finished_statements = self.finish_statements(prepared_statements)
        except self.ExtractorReturnedNone:
            finished_statements = prepared_statements

        self._creating_statements = False

        return finished_statements


class ClassConverter(Converter):
    """
    This is a base class for any converter that wants to create a class instance.
    """
    field_searcher_classes = []

    def __init__(self, document, related_object, django_project, test_case):
        super().__init__(document, related_object, django_project, test_case)
        self._fields = None
        self._blocked_argument_tokens = []
        self._last_document_word = None

    def block_token_as_argument(self, token):
        """Use this function to block a specific token from being taken as an argument."""
        if token and token not in self._blocked_argument_tokens:
            self._blocked_argument_tokens.append(token)

    @property
    def last_document_word(self):
        """Returns the last word of the document as a cached property."""
        if self._last_document_word is None:
            last_word = NoToken()
            for i in range(len(self.document)):
                end_token = self.document[-(i + 1)]

                if not end_token.is_punct:
                    last_word = end_token
                    break
            self._last_document_word = last_word
        return self._last_document_word

    def token_can_be_argument(self, token):
        """Checks if a given token can represent an argument of the __init__ from the class"""
        # first word is always a keyword from Gherkin
        if self.document[0] == token:
            return False

        if any([blocked_token and blocked_token == token for blocked_token in self._blocked_argument_tokens]):
            return False

        if token.pos_ != 'ADJ' and token.pos_ != 'NOUN' and token.pos_ != 'VERB' and token.pos_ != 'ADV':
            if token.pos_ != 'PROPN':
                return False

            if self.token_can_be_argument(token.head):
                return False

        # verbs with aux are fine (is done, ist abgeschlossen)
        if token.pos_ == 'VERB' and token.head.pos_ != 'AUX':
            return False

        # if there is a verb where the parent is a finites Modalverb (e.g. sollte), it should not be an argument
        if token == self.last_document_word and token_is_verb(token) and token.head.tag_ == 'VMFIN':
            return False

        return True

    def get_searcher_kwargs(self):
        """Returns the kwargs that are passed to the `search` method from a searcher."""
        return {}

    def search_for_init_argument(self, span, token):
        """
        This method will use searcher to search for an argument of the class. It will observe the span and
        the token and will return whatever the searcher returns.
        """
        searcher_kwargs = self.get_searcher_kwargs()

        search_texts = []
        if span:
            search_texts += [str(span), str(span.root.lemma_)]

        if token and str(token) not in search_texts:
            search_texts.append(str(token))

        for index, searcher_class in enumerate(self.field_searcher_classes):
            last_searcher_class = index == len(self.field_searcher_classes) - 1

            best_search_result = None
            highest_similarity = 0

            for search_text_index, search_text in enumerate(search_texts):
                searcher = searcher_class(search_text, src_language=self.language)

                # only raise no exception if it is the last searcher class and the last text to have a fallback
                last_search_text = search_text_index == len(search_texts) - 1
                raise_exception = not last_search_text or not last_searcher_class

                try:
                    search_result = searcher.search(**searcher_kwargs, raise_exception=raise_exception)
                    if best_search_result is None or searcher.highest_similarity > highest_similarity:
                        best_search_result = search_result
                        highest_similarity = searcher.highest_similarity

                        if highest_similarity > 0.9:
                            break
                except NoConversionFound:
                    pass

            if best_search_result is not None:
                return best_search_result

        return None

    def is_valid_search_result(self, search_result):
        """This method can be used to filter out specific search results before they are turned into extractors."""
        return bool(search_result)

    def get_default_argument_wrappers(self) -> [ConverterInitArgumentWrapper]:
        """Returns a list of default arguments wrappers. For each the selected value will be forced."""
        return []

    def get_argument_wrappers(self) -> [ConverterInitArgumentWrapper]:
        """
        Returns a list of objects that hold a token and the representative for an argument of the __init__ for the
        class. These objects are used to create extractors.
        """
        default_argument_wrappers = self.get_default_argument_wrappers()
        argument_wrappers = []

        for token in get_non_stop_tokens(self.document):
            if not self.token_can_be_argument(token):
                continue

            chunk = get_noun_chunk_of_token(token, self.document)
            representative = self.search_for_init_argument(chunk, token)

            # if the result is not valid, skip it
            if not self.is_valid_search_result(representative):
                continue

            # if the representative is already present, skip it
            if representative in [wrapper.representative for wrapper in argument_wrappers]:
                continue

            wrapper = ConverterInitArgumentWrapper(representative=representative, token=token)
            argument_wrappers.append(wrapper)

        # add default values if needed
        wrapper_identifiers = [wrapper.identifier for wrapper in argument_wrappers]
        for default_wrapper in default_argument_wrappers:
            if default_wrapper.identifier not in wrapper_identifiers:
                # force the result of the defaults
                default_wrapper.source_represents_output = True
                argument_wrappers.append(default_wrapper)

        return argument_wrappers

    def get_extractor_class(self, argument_wrapper: ConverterInitArgumentWrapper):
        """This returns the extractor class based on the ConverterInitArgumentWrapper."""
        raise NotImplementedError()

    def get_extractor_kwargs(self, argument_wrapper: ConverterInitArgumentWrapper, extractor_cls):
        """Returns the kwargs that are passed to the extractor to instanciate it."""
        return {
            'test_case': self.test_case,
            'source': argument_wrapper.token,
            'document': self.document,
            'representative': argument_wrapper.representative,
        }

    def get_extractor_instance(self, argument_wrapper: ConverterInitArgumentWrapper, extractor_class=None):
        """Returns an instance of an extractor for a given argument wrapper."""
        if extractor_class is None:
            extractor_class = self.get_extractor_class(argument_wrapper=argument_wrapper)

        kwargs = self.get_extractor_kwargs(
            argument_wrapper=argument_wrapper,
            extractor_cls=extractor_class,
        )

        instance = extractor_class(**kwargs)
        if argument_wrapper.source_represents_output:
            instance.source_represents_output = True
        return instance

    def get_extractors(self):
        """Returns the extractors for this converter."""
        wrappers = self.get_argument_wrappers()

        return [self.get_extractor_instance(argument_wrapper=wrapper) for wrapper in wrappers]

    def get_statements_from_datatable(self):
        """
        Handles if the passed Step has a data table. It will get the normal extractors and append any values that
        are passed by the data table. The extractors are added to the existing list. For each row of the
        data table the statements are created again.
        """
        statements = []
        datatable = self.related_object.argument
        column_names = datatable.get_column_names()

        for row in datatable.rows:
            extractors_copy = self.extractors.copy()

            for index, cell in enumerate(row.cells):
                representative = self.search_for_init_argument(span=None, token=column_names[index])

                # filter any invalid search results
                if not self.is_valid_search_result(representative):
                    continue

                wrapper = ConverterInitArgumentWrapper(token=cell.value, representative=representative)
                extractor_instance = self.get_extractor_instance(argument_wrapper=wrapper)

                existing_extract_index = -1
                for extractor_index, extractor in enumerate(extractors_copy):
                    if extractor.representative == representative:
                        existing_extract_index = extractor_index
                        break

                if existing_extract_index >= 0:
                    extractors_copy[existing_extract_index] = extractor_instance
                else:
                    extractors_copy.append(extractor_instance)

            statements += self.get_statements_from_extractors(extractors_copy)

        return statements
