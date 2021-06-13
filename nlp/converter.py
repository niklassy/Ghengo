from generate.suite import ModelFactoryExpression, AssignmentStatement
from generate.utils import to_function_name
from nlp.extractor import ModelFieldExtractor, SpanModelFieldExtractor
from nlp.generate.variable import Variable
from nlp.searcher import ModelSearcher, NoConversionFound, ModelFieldSearcher
from nlp.translator import ModelFieldTranslator
from nlp.utils import get_noun_chunks, is_proper_noun_of, token_references, get_non_stop_tokens


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
        self.model_noun_token = None
        self._extractors = []

    def get_statements(self, extractors):
        factory_kwargs = []
        statements = []

        factory_statement = ModelFactoryExpression(self._model, factory_kwargs)
        variable = Variable(
            name_predetermined=self.get_variable_text(self.model_noun_token),
            reference_string=factory_statement.to_template(),
        )
        statement = AssignmentStatement(expression=factory_statement, variable=variable)
        statements.append(statement)

        for translator in extractors:
            kwargs = translator.get_kwarg()
            if kwargs:
                factory_kwargs.append(kwargs)
            translator.append_side_effect_statements(statements)

        return statements

    def get_variable_text(self, root_noun):
        """
        Returns the text that will be the variable of the model factory.
        """
        try:
            next_token = self.document[root_noun.i + 1]

            # check for any Proper Nouns (nouns that describe/ give a name to a noun)
            if is_proper_noun_of(next_token, root_noun):
                return to_function_name(str(next_token))
        except IndexError:
            pass

        # search for real names like 'Alice'
        for named_entity in self.document.ents:
            for token in named_entity:
                if token_references(token, root_noun):
                    return to_function_name(str(token))

        # sometimes the variable can be defined as '1', e.g. order 1
        for child in root_noun.children:
            if child.is_digit:
                return str(child)

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
                extractors_copy.append(
                    ModelFieldTranslator(
                        test_case=test_case,
                        predetermined_value=cell.value,
                        model=self._model,
                        field=field,
                        source=None,
                    )
                )

            statements += self.get_statements(extractors_copy)

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

    def get_field_with_span(self, span, token=None):
        # TODO: clean - search span and token
        # all the following nouns will reference fields of that model, so find a field
        field_searcher_span = ModelFieldSearcher(text=str(span), src_language=self.language)

        # try to find something for whole span first
        try:
            return field_searcher_span.search(raise_exception=True, model_interface=self._model)
        # if nothing is found, try the root instead
        except NoConversionFound:
            token = span.root if span.root.pos_ == 'NOUN' else token
            field_searcher_root = ModelFieldSearcher(text=str(token), src_language=self.language)
            return field_searcher_root.search(model_interface=self._model)

    def get_noun_chunk_of_token(self, token):
        for chunk in self.get_noun_chunks():
            if token in chunk:
                return chunk
        return None

    def get_fields(self, test_case):
        """
        Main points to improve everything:
            - more reliable way of handling variables in the test generation
                - is a variable already defined?
                - find a variable for a given context
                - have only one point to create variable names
            - improve the extraction of fields and data
        """

        fields = []
        non_stop_tokens = get_non_stop_tokens(self.document)

        handled_non_stop = []
        unhandled_noun_chunks = self.get_noun_chunks()[1:].copy()
        unhandled_propn_chunk = None
        for non_stop_token in non_stop_tokens:
            if non_stop_token.i < self.get_noun_chunks()[0].end or non_stop_token.head == self.model_noun_token:
                handled_non_stop.append(non_stop_token)
                continue

            # there are two ways to detect a field:
            #   1) by noun chunks
            #   2) by using the stop tokens
            #       a token references another which can be extracted by the `head` attribute

            head = non_stop_token.head
            try:
                current_noun_chunk = unhandled_noun_chunks[0]
            except IndexError:
                continue

            # clean the noun chunks
            if non_stop_token in current_noun_chunk:
                if non_stop_token == current_noun_chunk[-1]:
                    unhandled_noun_chunks.remove(current_noun_chunk)

                if current_noun_chunk.root.pos_ == 'PROPN':
                    unhandled_propn_chunk = current_noun_chunk
                    continue
            elif current_noun_chunk[-1] not in non_stop_tokens:
                unhandled_noun_chunks.remove(current_noun_chunk)

            if non_stop_token in handled_non_stop:
                continue

            if head in non_stop_tokens and head not in handled_non_stop:
                field_token = head
                field_value_token = non_stop_token
            elif unhandled_propn_chunk:
                field_token = non_stop_token
                field_value_token = unhandled_propn_chunk.root
            elif current_noun_chunk.root.pos_ == 'NOUN':
                field_token = current_noun_chunk.root
                field_value_token = None

                for token in current_noun_chunk:
                    if is_proper_noun_of(token, field_token):
                        field_value_token = token
                        break
            else:
                continue

            noun_chunk = self.get_noun_chunk_of_token(field_token)
            field = self.get_field_with_span(noun_chunk, field_token)

            handled_non_stop.append(head)
            handled_non_stop.append(non_stop_token)
            unhandled_propn_chunk = None

            if field in [f for f, _, _ in fields]:
                continue

            fields.append((field, field_token, field_value_token))

        return [ModelFieldTranslator(test_case, value_token, field_token, self._model, field) for field, field_token, value_token in fields]

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

            field = self.get_field_with_span(noun_chunk)

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

        self._extractors = self.get_fields(test_case)

        if not self.related_object.has_datatable:
            return self.get_statements(self._extractors)

        return self._get_statements_with_datatable(test_case)
