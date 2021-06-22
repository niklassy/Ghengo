from django_meta.project import AbstractModelInterface
from nlp.generate.argument import Kwarg, Argument
from nlp.generate.expression import ModelFactoryExpression
from nlp.generate.importer import Importer
from nlp.generate.statement import AssignmentStatement, Statement, ModelFieldAssignmentStatement
from nlp.generate.utils import to_function_name
from nlp.generate.variable import Variable
from nlp.searcher import ModelSearcher, NoConversionFound, ModelFieldSearcher
from nlp.extractor import ModelFieldExtractor, get_model_field_extractor
from nlp.utils import get_noun_chunks, is_proper_noun_of, get_non_stop_tokens, \
    get_noun_chunk_of_token, token_is_noun, get_root_of_token, NoToken, token_to_function_name, token_is_proper_noun


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

    def build_statement(self, *args, **kwargs):
        """Creates an instance of the statement that was defined by this converter."""
        return self.statement_class(**self.get_statement_kwargs(*args, **kwargs))

    def get_statement_kwargs(self, *args, **kwargs):
        """Returns the kwargs that are used to create a statement."""
        return {}

    def get_expression_kwargs(self, *args, **kwargs):
        """Returns all kwargs that are used to create the expression."""
        return {}

    def build_expression(self, *args, **kwargs):
        """Returns an instance if the expression that this converter uses."""
        return self.get_expression_class()(**self.get_expression_kwargs(*args, **kwargs))

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
        extractor.on_handled_by_converter(statements)

    def get_base_statements(self):
        return []

    def get_statements_from_extractors(self, extractors):
        """Function to return statements based on extractors."""
        statements = self.get_base_statements()

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

    def get_base_statements(self):
        return [self.build_statement()]

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
                future_name = token_to_function_name(child)
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

    @property
    def variable_name(self):
        """Returns the name of the variable that the factory statement will have (if any)."""
        if self._variable_name is None:
            self._variable_name = token_to_function_name(self.variable_token)
        return self._variable_name

    @property
    def model_noun_chunk(self):
        noun_chunks = self.get_noun_chunks()
        return noun_chunks[0]

    @property
    def model_token(self):
        """
        Returns the token that represents the model
        """
        if self._model_token is None:
            noun_chunks = self.get_noun_chunks()
            model_noun_chunk = noun_chunks[0]
            self._model_token = self.model_noun_chunk.root
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


class ModelVariableReferenceConverter(ModelFactoryConverter):
    expression_class = Argument
    statement_class = ModelFieldAssignmentStatement

    def __init__(self, document, related_object, django_project, test_case):
        super().__init__(document, related_object, django_project, test_case)
        self._model_determined = False
        self._referenced_variable = None
        self._referenced_variable_determined = False

    def get_document_compatibility(self):
        if self.referenced_variable:
            return 1
        return 0

    @property
    def variable_token(self):
        if self._variable_token is None:
            for statement in self.test_case.statements:
                if not isinstance(statement.expression, ModelFactoryExpression):
                    continue

                model = self.model_interface or statement.expression.model_interface

                for token in self.model_noun_chunk:

                    future_name = token_to_function_name(token)
                    variable_in_tc = self.test_case.variable_defined(future_name, model.name)

                    if (token.is_digit or token_is_proper_noun(token)) and variable_in_tc:
                        self._variable_token = token
                        break

                if self._variable_token is not None:
                    break

            if self._variable_token is None:
                self._variable_token = NoToken()

        return self._variable_token

    @property
    def referenced_variable(self):
        if self._referenced_variable_determined is False:
            variable_token = self.variable_token

            for statement in self.test_case.statements:
                if not isinstance(statement.expression, ModelFactoryExpression):
                    continue

                model = self.model_interface or statement.expression.model_interface
                future_name = token_to_function_name(variable_token)

                if statement.string_matches_variable(future_name, model.name):
                    self._referenced_variable = statement.variable.copy()
                    break

            self._referenced_variable_determined = True
        return self._referenced_variable

    @property
    def variable_name(self):
        if self._variable_name is None:
            referenced_variable = self.referenced_variable

            if referenced_variable:
                self._variable_name = referenced_variable.name
            else:
                self._variable_name = ''

        return self._variable_name

    @property
    def model_interface(self):
        if self._referenced_variable is not None and self._referenced_variable_determined:
            self._model = self._referenced_variable.value.model_interface
            return self._model

        if self._model_determined is False:
            model_searcher = ModelSearcher(text=str(self.model_token.lemma_), src_language=self.language)
            model = None

            try:
                search_result_model = model_searcher.search(project_interface=self.django_project, raise_exception=True)
            except NoConversionFound:
                search_result_model = None

            if search_result_model:
                for statement in self.test_case.statements:
                    exp = statement.expression
                    if isinstance(exp, ModelFactoryExpression) and search_result_model.model == exp.model_interface.model:
                        model = search_result_model
                        break

            self._model_determined = True
            self._model = model
        return self._model

    def get_expression_kwargs(self, *args, **kwargs):
        return {'value': kwargs.get('value')}

    def get_statement_kwargs(self, *args, **kwargs):
        extractor = kwargs.get('extractor')
        exp = self.build_expression(value=extractor.extract_value())

        return {
            'variable': self.referenced_variable,
            'assigned_value': exp,
            'field_name': extractor.field_name,
        }

    def handle_extractor(self, extractor, statements):
        statement = self.build_statement(extractor=extractor)
        statements.append(statement)

    def get_statements_from_extractors(self, extractors):
        statements = super().get_statements_from_extractors(extractors)
        # TODO: add save statement
        # statements.append()
        return statements

    def get_base_statements(self):
        return []
