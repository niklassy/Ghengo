from django_meta.project import AbstractModelInterface
from nlp.generate.expression import ModelFactoryExpression
from nlp.generate.importer import Importer
from nlp.generate.statement import AssignmentStatement, Statement
from nlp.generate.utils import to_function_name
from nlp.generate.variable import Variable
from nlp.searcher import ModelSearcher, NoConversionFound, ModelFieldSearcher
from nlp.extractor import ModelFieldExtractor
from nlp.utils import get_noun_chunks, is_proper_noun_of, token_references, get_non_stop_tokens, \
    get_noun_chunk_of_token, get_proper_noun_of_chunk, token_is_noun, token_is_verb, token_is_proper_noun, \
    get_root_of_token, get_noun_from_chunk, get_proper_noun_from_chunk


class NoToken:
    def __eq__(self, other):
        return False


class Converter(object):
    """
    A converter is a class that converts a given document to code.

    You have to pass a spacy document and it will convert it into code.

    It most likely will do the following:
        1) Find elements/ django classes etc. that match the document
        2) Extract the data to use that class/ element from the text
        3) Create the statements that will become templates sooner or later
    """
    statement_class = Statement
    expression_class = None

    def __init__(self, document, related_object, django_project, test_case):
        self.document = document
        self.django_project = django_project
        self.related_object = related_object
        self.language = document.lang_
        self.test_case = test_case

    @property
    def extractors(self):
        raise NotImplementedError()

    def get_noun_chunks(self):
        """Returns all the noun chunks from the document."""
        return get_noun_chunks(self.document)

    def build_statement(self):
        """Creates an instance of the statement that was defined by this converter."""
        return self.statement_class(**self.get_statement_kwargs())

    def get_statement_kwargs(self):
        """Returns the kwargs that are used to create a statement."""
        return {}

    def get_expression_kwargs(self):
        """Returns all kwargs that are used to create the expression."""
        return {}

    def build_expression(self):
        """Returns an instance if the expression that this converter uses."""
        return self.get_expression_class()(**self.get_expression_kwargs())

    def get_expression_class(self):
        """Returns the class of the expression that this converter uses."""
        return Importer.get_class(self.expression_class, self.test_case.type)

    def convert_to_statements(self):
        """
        Converts the document to statements.

        Returns:
            a list of Statements
        """
        return self.get_statements_from_extractors(self.extractors)

    def get_document_compatibility(self):
        """
        Returns the compatibility of a document. This represents how well this converter fits the given document.

        Returns:
            value from 0-1
        """
        return 1

    def handle_extractor(self, extractor, statements):
        """Does everything that is needed when an extractor is called."""
        # some extractors add more statements, so add them here if needed
        extractor.append_side_effect_statements(statements)

    def get_statements_from_extractors(self, extractors):
        """Function to return statements based on extractors."""
        statements = [self.build_statement()]

        # go through each extractor and append its kwargs to the factory kwargs
        for extractor in extractors:
            self.handle_extractor(extractor, statements)

        return statements


class ModelFactoryConverter(Converter):
    """
    This converter will convert a document into a model factory statement and everything that belongs to it.
    """
    statement_class = AssignmentStatement
    expression_class = ModelFactoryExpression

    def __init__(self, document, related_object, django_project, test_case):
        super().__init__(document, related_object, django_project, test_case)
        self._model = None
        self._model_token = None
        self._variable_name = None
        self._variable_token = None
        self._extractors = None

    def get_document_compatibility(self):
        compatibility = 1

        if isinstance(self.model_interface, AbstractModelInterface):
            compatibility *= 0.8

        # models are normally displayed by nouns
        if not token_is_noun(self.model_token):
            compatibility *= 0.01

        # If the root of the document is a finites Modalverb (e.g. sollte) it is rather inlikely that the creation of
        # a model is meant
        root = get_root_of_token(self.model_token)
        if root and root.tag_ == 'VMFIN':
            compatibility *= 0.4

        return compatibility

    def get_statement_kwargs(self):
        expression = self.build_expression()
        variable = Variable(
            name_predetermined=self.variable_name,
            reference_string=self.variable_reference_string,
        )
        return {'expression': expression, 'variable': variable}

    def get_expression_kwargs(self):
        return {'model_interface': self.model_interface, 'factory_kwargs': []}

    def handle_extractor(self, extractor, statements):
        """Get the kwargs for the expression from the extractor."""
        super().handle_extractor(extractor, statements)
        factory_kwargs = statements[0].expression.function_kwargs

        kwarg = extractor.get_kwarg()
        if kwarg:
            factory_kwargs.append(kwarg)

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

            statements += self.get_statements_from_extractors(extractors_copy)

        return statements

    @property
    def variable_reference_string(self):
        return self.model_interface.name

    @property
    def variable_token(self):
        if self._variable_token is None:
            for child in self.model_token.children:
                future_name = self._get_variable_name(child)
                variable_in_tc = self.test_case.variable_defined(future_name, self.variable_reference_string)

                # sometimes nlp gets confused about variables and what belongs to this model factory and
                # what is a reference to an older variable - so if there is a variable with the exact same name
                # we assume that that token is not valid
                if (child.is_digit or is_proper_noun_of(child, self.model_token)) and not variable_in_tc:
                    self._variable_token = child
                    break

            if self._variable_token is None:
                self._variable_token = NoToken()

        return self._variable_token

    @classmethod
    def _get_variable_name(cls, token):
        """Helper function that translates a token into a variable name."""
        if isinstance(token, NoToken):
            return ''
        elif token.is_digit:
            return str(token)
        else:
            return to_function_name(str(token))

    @property
    def variable_name(self):
        """Returns the name of the variable that the factory statement will have (if any)."""
        if self._variable_name is None:
            self._variable_name = self._get_variable_name(self.variable_token)
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
        if span:
            field_searcher_span = ModelFieldSearcher(text=str(span), src_language=self.language)

            try:
                return field_searcher_span.search(raise_exception=True, model_interface=self.model_interface)
            except NoConversionFound:
                pass

            field_searcher_root = ModelFieldSearcher(text=str(span.root.lemma_), src_language=self.language)
            try:
                return field_searcher_root.search(raise_exception=bool(token), model_interface=self.model_interface)
            except NoConversionFound:
                pass

        if token:
            field_searcher_token = ModelFieldSearcher(text=str(token.lemma_), src_language=self.language)
            return field_searcher_token.search(model_interface=self.model_interface)

        return None

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
                if non_stop_token.i < model_noun_chunk.end or self.variable_token == non_stop_token:
                    handled_non_stop.append(non_stop_token)
                    continue

                # get the head of the non_stop_token
                head = non_stop_token.head

                # extract the current noun_chunk
                try:
                    noun_chunk = unhandled_noun_chunks[0]
                except IndexError:
                    noun_chunk = []

                # ========== CLEAN NOUN_CHUNKS ==========
                if non_stop_token in noun_chunk:
                    # if the current token is the last one in the chunk, mark the chunk as handled
                    if non_stop_token == noun_chunk[-1]:
                        unhandled_noun_chunks.remove(noun_chunk)

                    # if the root of the chunk is a proper noun (normally a noun), it needs to be handled later
                    if get_noun_from_chunk(noun_chunk) is None and get_proper_noun_from_chunk(noun_chunk):
                        unhandled_propn_chunk = noun_chunk
                        continue
                # if the last token of that chunk is not present in the non stop tokens, mark the chunk as handled
                elif bool(noun_chunk) and noun_chunk[-1] not in non_stop_tokens:
                    unhandled_noun_chunks.remove(noun_chunk)

                # if the token was already handled, continue
                if non_stop_token in handled_non_stop:
                    continue

                # ========== GET VALUE AND SOURCE ===========
                # if the head is in the non stop tokens and not already handled, it is considered the field
                # and the token is the value
                noun_or_verb_head = token_is_noun(head) or token_is_verb(head, include_aux=False)
                if head in non_stop_tokens and head not in model_noun_chunk and noun_or_verb_head:
                    field_token = head
                    field_value_token = non_stop_token

                # if there was an unhandled proper noun, the token is the field and the value is the root of the
                # unhandled proper noun
                elif unhandled_propn_chunk:
                    field_token = non_stop_token
                    field_value_token = get_proper_noun_from_chunk(unhandled_propn_chunk)

                # if the root of the current noun chunk is a noun, that noun is the field; the value is the proper
                # noun of of that chunk
                elif bool(noun_chunk) and token_is_noun(noun_chunk.root):
                    field_token = noun_chunk.root
                    field_value_token = get_proper_noun_of_chunk(field_token, noun_chunk)

                # above we checked the head of the non stop token, check the token itself here too
                elif token_is_noun(non_stop_token) or token_is_verb(non_stop_token, include_aux=False):
                    field_token = non_stop_token
                    field_value_token = get_proper_noun_of_chunk(field_token, noun_chunk)

                else:
                    continue

                # ========== GET FIELD ==========
                noun_chunk = get_noun_chunk_of_token(field_token, self.document)
                field = self._search_for_field(span=noun_chunk, token=field_token)

                if field is None:
                    continue

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
            return self.get_statements_from_extractors(self.extractors)

        return self._get_statements_with_datatable()
