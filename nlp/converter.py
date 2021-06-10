from generate.suite import ModelFactoryExpression, AssignmentStatement, Kwarg
from generate.utils import to_function_name
from nlp.extractor import ModelFieldExtractor, SpanModelFieldExtractor
from nlp.searcher import ModelSearcher, NoConversionFound, ModelFieldSearcher
from nlp.utils import get_noun_chunks, is_proper_noun_of, token_references


class Converter(object):
    """
    A converter is a class that converts a given document to code.

    You have to pass a spacy document and it will convert it into code.

    It most likely will do the following:
        1) Find elements/ django classes etc. that match the document
        2) Extract the data to use that class/ element from the text
        3) Create the statements that will become templates sooner or later
    """
    def __init__(self, document, related_object, django_project):
        self.document = document
        self.django_project = django_project
        self.related_object = related_object
        self.language = document.lang_

    def get_noun_chunks(self):
        """Returns all the noun chunks from the document."""
        return get_noun_chunks(self.document)

    def convert_to_statements(self, test_case):
        """
        Converts the document to statements.

        Returns:
            a list of Statements
        """
        raise NotImplementedError()

    def get_document_fitness(self):
        """
        Returns the fitness of a document. This represents how well this converter fits the given document.

        Returns:
            value from 0-1
        """
        raise NotImplementedError()


class ModelFactoryConverter(Converter):
    def __init__(self, document, related_object, django_project):
        super().__init__(document, related_object, django_project)
        self._model = None
        self._extractors = []

    def create_statement(self, extractors, test_case):
        """
        Creates a statement for a test case.

        To do that, we need the field name, the value of the field and the model.
        The model was already determined.
        The fields were also already determined.
        Now, we need to get the values of these fields.
        """
        factory_kwargs = []

        for extractor in extractors:
            # check if the value could be a function
            valid_fn = extractor.value_can_be_function_name()
            # grab the value for python
            python_value = extractor.extract_python_value()
            # check if the value should be a variable (currently determined by checking if that value already exists)
            as_variable = valid_fn and test_case.variable_defined(to_function_name(python_value))

            # convert to a function name if it is defined as a variable
            if as_variable:
                value = to_function_name(python_value)
            else:
                value = python_value

            factory_kwargs.append(Kwarg(extractor.field_name, value, as_variable=as_variable))

        factory_statement = ModelFactoryExpression(self._model, factory_kwargs)
        return AssignmentStatement(expression=factory_statement, variable=self.get_variable_text(self.model_noun_token))

    def get_variable_text(self, root_noun):
        """
        Returns the text that will be the variable of the model factory.
        """
        try:
            next_token = self.document[root_noun.i + 1]
        except IndexError:
            return None

        if is_proper_noun_of(next_token, root_noun):
            return to_function_name(str(next_token))

        for named_entity in self.document.ents:
            for token in named_entity:
                if token_references(token, root_noun):
                    return to_function_name(str(token))

        return None

    def get_document_fitness(self):
        """For now, this is only used as the single converter in GIVEN. So just return 1."""
        return 1

    def _get_statements_with_datatable(self, test_case):
        """
        If a there is a data table on the step, it is assumed that it contains data to create the model entry.
        In that case, use the extractors that already exist and append the ones that are defined in the table.
        """
        statements = []
        datatable = self.related_object.argument
        column_names = datatable.get_column_names()

        for row in datatable.rows:
            extractors_copy = self._extractors.copy()

            for index, cell in enumerate(row.cells):
                field_searcher = ModelFieldSearcher(column_names[index], src_language=self.language)
                field = field_searcher.search(model_interface=self._model)
                extractors_copy.append(ModelFieldExtractor(self._model, cell.value, field))

            statements.append(self.create_statement(extractors_copy, test_case))

        return statements

    def _initialize_model(self):
        """
        Find the model for the given statement and save data so that it can be accessed later.

        The model can be found in the first chunk:
            => Gegeben sei ein Benutzer ...
            => Given a user ...
        """
        self._model = None
        noun_chunks = self.get_noun_chunks()
        model_noun_chunk = noun_chunks[0]
        self.model_noun_token = model_noun_chunk.root
        model_searcher = ModelSearcher(text=str(self.model_noun_token), src_language=self.language)
        self._model = model_searcher.search(project_interface=self.django_project)

    def _initialize_fields(self):
        self._extractors = []
        noun_chunks = self.get_noun_chunks()
        unhandled_propn = None

        # first entry will contain the model, so skip it
        for index, noun_chunk in enumerate(noun_chunks[1:]):
            # filter out any noun chunks without a noun
            if noun_chunk.root.pos_ != 'NOUN':
                # if it is a proper noun, it will be handled later
                # Proper nouns represent names like "Alice" "todo1" and so on. They describe other nouns in detail
                # If one is found here, it will probably be used in a later noun chunk
                if noun_chunk.root.pos_ == 'PROPN':
                    unhandled_propn = noun_chunk.root
                continue

            # all the following nouns will reference fields of that model, so find a field
            field_searcher_span = ModelFieldSearcher(text=str(noun_chunk), src_language=self.language)

            # try to find something for whole span first
            try:
                field = field_searcher_span.search(raise_exception=True, model_interface=self._model)
            # if nothing is found, try the root instead
            except NoConversionFound:
                field_searcher_root = ModelFieldSearcher(text=str(noun_chunk.root), src_language=self.language)
                field = field_searcher_root.search(model_interface=self._model)

            # search for any tokens that reference the root element - which means that they contain the value for
            # that field
            field_value_token = None
            for token in noun_chunk:
                if is_proper_noun_of(token, noun_chunk.root):
                    field_value_token = token
                    break

            # if the current noun_chunk does not contain a PROPN that references the root, grab the one that was
            # not handled yet
            if field_value_token is None and unhandled_propn is not None:
                self._extractors.append(ModelFieldExtractor(self._model, unhandled_propn, field))
            else:
                self._extractors.append(SpanModelFieldExtractor(self._model, noun_chunk, field))

    def convert_to_statements(self, test_case):
        # first get the model
        self._initialize_model()

        # get the fields afterwards, which will initialize a statement
        self._initialize_fields()

        if not self.related_object.has_datatable:
            return [self.create_statement(self._extractors, test_case)]

        return self._get_statements_with_datatable(test_case)
