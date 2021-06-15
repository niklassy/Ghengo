from django_meta.project import AbstractModelInterface
from nlp.generate.pytest.expression import PyTestModelFactoryExpression
from nlp.generate.statement import AssignmentStatement
from nlp.generate.utils import to_function_name
from nlp.generate.variable import Variable
from nlp.searcher import ModelSearcher, NoConversionFound, ModelFieldSearcher
from nlp.extractor import ModelFieldExtractor
from nlp.utils import get_noun_chunks, is_proper_noun_of, token_references, get_non_stop_tokens, get_noun_chunk_of_token


class Converter(object):
    """
    A converter is a class that converts a given document to code.

    You have to pass a spacy document and it will convert it into code.

    It most likely will do the following:
        1) Find elements/ django classes etc. that match the document
        2) Extract the data to use that class/ element from the text
        3) Create the statements that will become templates sooner or later
    """
    statement_class = None

    def __init__(self, document, related_object, django_project, test_case):
        self.document = document
        self.django_project = django_project
        self.related_object = related_object
        self.language = document.lang_
        self.test_case = test_case

    def get_noun_chunks(self):
        """Returns all the noun chunks from the document."""
        return get_noun_chunks(self.document)

    def build_statement(self, *args, **kwargs):
        return self.statement_class(**self.get_statement_kwargs(*args, **kwargs))

    def get_statement_kwargs(self, *args, **kwargs):
        return {}

    def get_statements(self, extractors):
        raise NotImplementedError()

    def convert_to_statements(self):
        """
        Converts the document to statements.

        Returns:
            a list of Statements
        """
        raise NotImplementedError()

    def get_document_compatibility(self):
        """
        Returns the fitness of a document. This represents how well this converter fits the given document.

        Returns:
            value from 0-1
        """
        return 1


class ModelFactoryConverter(Converter):
    """
    This converter will convert a document into a model factory statement and everything that belongs to it.
    """
    statement_class = AssignmentStatement

    def __init__(self, document, related_object, django_project, test_case):
        super().__init__(document, related_object, django_project, test_case)
        self._model = None
        self._model_token = None
        self._variable_name = None
        self._extractors = None

    def get_statement_kwargs(self, *args, **kwargs):
        # TODO: implement way to change for different testing types
        factory_statement = PyTestModelFactoryExpression(*args, **kwargs)
        variable = Variable(
            name_predetermined=self.variable_name,
            reference_string=self._model.model.__name__,
        )
        return {'expression': factory_statement, 'variable': variable}

    def get_statements(self, extractors):
        factory_kwargs = []
        # create the initial statement
        statements = [self.build_statement(self.model_interface, factory_kwargs=factory_kwargs)]

        # go through each extractor and append its kwargs to the factory kwargs
        for extractor in extractors:
            kwargs = extractor.get_kwarg()
            if kwargs:
                factory_kwargs.append(kwargs)

            # some extractors add more statements, so add them here if needed
            extractor.append_side_effect_statements(statements)

        return statements

    def get_document_compatibility(self):
        compatibility = 1

        if isinstance(self.model_interface, AbstractModelInterface):
            compatibility *= 0.5

        # models are normally displayed by nouns
        if self.model_token.pos_ != 'NOUN':
            compatibility *= 0.2

        return compatibility

    def _get_statements_with_datatable(self):
        """
        If a there is a data table on the step, it is assumed that it contains data to create the model entry.
        In that case, use the extractors that already exist and append the ones that are defined in the table.
        """
        statements = []
        datatable = self.related_object.argument
        column_names = datatable.get_column_names()

        for row in datatable.rows:
            extractors_copy = self.extractors.copy()

            for index, cell in enumerate(row.cells):
                field_searcher = ModelFieldSearcher(column_names[index], src_language=self.language)
                field = field_searcher.search(model_interface=self.model_interface)
                extractors_copy.append(
                    ModelFieldExtractor(
                        test_case=self.test_case,
                        predetermined_value=cell.value,
                        model_interface=self.model_interface,
                        field=field,
                        source=None,
                    )
                )

            statements += self.get_statements(extractors_copy)

        return statements

    @property
    def variable_name(self):
        if self._variable_name is None:
            try:
                next_token = self.document[self.model_token.i + 1]

                # check for any Proper Nouns (nouns that describe/ give a name to a noun)
                if is_proper_noun_of(next_token, self.model_token):
                    self._variable_name = to_function_name(str(next_token))
                    return self._variable_name
            except IndexError:
                pass

            # search for real names like 'Alice'
            for named_entity in self.document.ents:
                for token in named_entity:
                    if token_references(token, self.model_token):
                        self._variable_name = to_function_name(str(token))
                    return self._variable_name

            # sometimes the variable can be defined as '1', e.g. order 1
            for child in self.model_token.children:
                if child.is_digit:
                    self._variable_name = str(child)
                    return self._variable_name

            self._variable_name = ''
        return self._variable_name

    @property
    def model_token(self):
        """
        Returns the token that represents the model
        """
        if self._model_token is None:
            noun_chunks = self.get_noun_chunks()
            model_noun_chunk = noun_chunks[0]
            self._model_token = model_noun_chunk.root
        return self._model_token

    @property
    def model_interface(self):
        """
        Returns the model interface that represents the model.
        """
        if self._model is None:
            model_searcher = ModelSearcher(text=str(self.model_token.lemma_), src_language=self.language)
            self._model = model_searcher.search(project_interface=self.django_project)
        return self._model

    def _search_for_field(self, span, token):
        """
        Searches for a field with a given span and token inside the self.model_interface
        """
        # all the following nouns will reference fields of that model, so find a field
        field_searcher_span = ModelFieldSearcher(text=str(span), src_language=self.language)

        # try to find something for whole span first
        try:
            return field_searcher_span.search(raise_exception=True, model_interface=self.model_interface)
        # if nothing is found, try the root instead
        except NoConversionFound:
            token = span.root if span.root.pos_ == 'NOUN' else token
            field_searcher_root = ModelFieldSearcher(text=str(token.lemma_), src_language=self.language)
            return field_searcher_root.search(model_interface=self.model_interface)

    @property
    def extractors(self):
        """
        Returns all the extractors. Each extractor gets the information about each field in the model factory
        statement.
        """
        if self._extractors is None:
            fields = []
            handled_non_stop = []
            non_stop_tokens = get_non_stop_tokens(self.document)

            # the first noun_chunk holds the model, so skip it
            unhandled_noun_chunks = self.get_noun_chunks()[1:].copy()
            unhandled_propn_chunk = None

            model_noun_chunk = get_noun_chunk_of_token(self.model_token, self.document)

            # go through each non stop token
            for non_stop_token in non_stop_tokens:
                # if that token is part of the model definition, skip it
                if non_stop_token.i < model_noun_chunk.end or non_stop_token.head == self.model_token:
                    handled_non_stop.append(non_stop_token)
                    continue

                # get the head of the non_stop_token
                head = non_stop_token.head

                # extract the current noun_chunk
                try:
                    current_noun_chunk = unhandled_noun_chunks[0]
                except IndexError:
                    continue

                # ========== CLEAN NOUN_CHUNKS ==========
                if non_stop_token in current_noun_chunk:
                    # if the current token is the last one in the chunk, mark the chunk as handled
                    if non_stop_token == current_noun_chunk[-1]:
                        unhandled_noun_chunks.remove(current_noun_chunk)

                    # if the root of the chunk is a proper noun (normally a noun), it needs to be handled later
                    if current_noun_chunk.root.pos_ == 'PROPN':
                        unhandled_propn_chunk = current_noun_chunk
                        continue
                # if the last token of that chunk is not present in the non stop tokens, mark the chunk as handled
                elif current_noun_chunk[-1] not in non_stop_tokens:
                    unhandled_noun_chunks.remove(current_noun_chunk)

                # if the token was already handled, continue
                if non_stop_token in handled_non_stop:
                    continue

                # ========== GET VALUE AND SOURCE ===========
                # if the head is in the non stop tokens and not already handled, it is considered the field
                # and the token is the value
                if head in non_stop_tokens and head not in handled_non_stop:
                    field_token = head
                    field_value_token = non_stop_token

                # if there was an unhandled proper noun, the token is the field and the value is the root of the
                # unhandled proper noun
                elif unhandled_propn_chunk:
                    field_token = non_stop_token
                    field_value_token = unhandled_propn_chunk.root

                # if the root of the current noun chunk is a noun, that noun is the field; the value is the proper
                # noun of of that chunk
                elif current_noun_chunk.root.pos_ == 'NOUN':
                    field_token = current_noun_chunk.root
                    field_value_token = None

                    for token in current_noun_chunk:
                        if is_proper_noun_of(token, field_token):
                            field_value_token = token
                            break
                else:
                    continue

                # ========== GET FIELD ==========
                noun_chunk = get_noun_chunk_of_token(field_token, self.document)
                field = self._search_for_field(span=noun_chunk, token=field_token)

                handled_non_stop.append(head)
                handled_non_stop.append(non_stop_token)
                unhandled_propn_chunk = None

                if field in [f for f, _, _ in fields]:
                    continue

                fields.append((field, field_token, field_value_token))

            # ========== BUILD EXTRACTORS ==========
            extractors = []
            for field, field_token, value_token in fields:
                extractors.append(
                    ModelFieldExtractor(self.test_case, value_token, field_token, self.model_interface, field))

            self._extractors = extractors
        return self._extractors

    def convert_to_statements(self):
        if not self.related_object.has_datatable:
            return self.get_statements(self.extractors)

        return self._get_statements_with_datatable()
