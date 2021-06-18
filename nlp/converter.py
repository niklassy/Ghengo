from django_meta.project import AbstractModelInterface
from nlp.generate.argument import Kwarg
from nlp.generate.expression import ModelFactoryExpression
from nlp.generate.importer import Importer
from nlp.generate.statement import AssignmentStatement, Statement
from nlp.generate.utils import to_function_name
from nlp.generate.variable import Variable
from nlp.searcher import ModelSearcher, NoConversionFound, ModelFieldSearcher
from nlp.extractor import ModelFieldExtractor, get_model_field_extractor
from nlp.utils import get_noun_chunks, is_proper_noun_of, get_non_stop_tokens, \
    get_noun_chunk_of_token, token_is_noun, get_root_of_token


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
        extractor.get_statements(statements)

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

        extracted_value = extractor.extract_value()
        if extracted_value is None:
            return

        kwarg = Kwarg(extractor.field_name, extracted_value)
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
                        model_interface=self.model_interface,
                        field=field,
                        source=cell.value,
                        document=self.document,
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
            field_searcher_token = ModelFieldSearcher(text=str(token), src_language=self.language)
            return field_searcher_token.search(model_interface=self.model_interface)

        return None

    @property
    def extractors(self):
        if self._extractors is None:
            fields = []

            for token in get_non_stop_tokens(self.document):
                if token == self.model_token or self.variable_token == token:
                    continue

                if token.pos_ != 'ADJ' and token.pos_ != 'NOUN' and token.pos_ != 'VERB':
                    continue

                # verbs with aux are fine (is done, ist abgeschlossen)
                if token.pos_ == 'VERB' and token.head.pos_ != 'AUX':
                    continue

                chunk = get_noun_chunk_of_token(token, self.document)
                field = self._search_for_field(chunk, token)

                if field in [f for f, _ in fields]:
                    continue

                fields.append((field, token))

            extractors = []

            for field, field_token in fields:
                extractor_cls = get_model_field_extractor(field)
                extractors.append(
                    extractor_cls(self.test_case, field_token, self.model_interface, field, self.document)
                )

            self._extractors = extractors
        return self._extractors

    def convert_to_statements(self):
        if not self.related_object.has_datatable:
            return self.get_statements_from_extractors(self.extractors)

        return self._get_statements_with_datatable()
