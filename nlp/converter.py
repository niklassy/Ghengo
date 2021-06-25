from django_meta.model import AbstractModelInterface
from nlp.generate.argument import Kwarg, Argument
from nlp.generate.expression import ModelFactoryExpression, ModelSaveExpression
from nlp.generate.statement import AssignmentStatement, ModelFieldAssignmentStatement
from nlp.generate.variable import Variable
from nlp.searcher import ModelSearcher, NoConversionFound, ModelFieldSearcher, UrlSearcher
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

    def convert_to_statements(self):
        """Converts the document into statements."""
        if not self.related_object.has_datatable:
            return self.get_statements_from_extractors(self.extractors)

        return self.get_statements_from_datatable()

    def get_statements_from_datatable(self):
        """If the converter supports special handling for datatables of a Step, overwrite this method."""
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


class ModelConverter(Converter):
    def __init__(self, document, related_object, django_project, test_case):
        super().__init__(document, related_object, django_project, test_case)
        self._model = None
        self._model_token = None
        self._variable_name = None
        self._variable_token = None
        self._extractors = None
        self._fields = None

    @property
    def model_noun_chunk(self):
        """Returns the noun chunk in which the model can be found."""
        noun_chunks = self.get_noun_chunks()
        return noun_chunks[0]

    @property
    def model_token(self):
        """
        Returns the token that represents the model. By default this is the root in the first noun chunk.
        `Given a user ...`.
        """
        if self._model_token is None:
            self._model_token = self.model_noun_chunk.root
        return self._model_token

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
    def model_interface(self):
        """
        Returns the model interface that represents the model.
        """
        if self._model is None:
            model_searcher = ModelSearcher(text=str(self.model_token.lemma_), src_language=self.language)
            self._model = model_searcher.search(project_interface=self.django_project)
        return self._model

    @property
    def variable_token(self):
        """
        Returns the variable that the document references. `Given a user *alice* with ...`
        """
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
    def variable_reference_string(self):
        """Returns the reference string that is passed to the variable of this document."""
        return self.model_interface.name

    @property
    def variable_name(self):
        """Returns the name of the variable that the factory statement will have (if any)."""
        if self._variable_name is None:
            self._variable_name = token_to_function_name(self.variable_token)
        return self._variable_name

    @property
    def fields(self):
        """Returns all the fields that the document references."""
        if self.model_interface is None:
            return []

        if self._fields is None:
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
            self._fields = fields
        return self._fields

    @property
    def extractors(self):
        """
        Returns all the extractors of this converter. The extractors are responsible to get the values for the fields.
        """
        if len(self.fields) == 0:
            return []

        if self._extractors is None:
            extractors = []

            for field, field_token in self.fields:
                extractor_cls = get_model_field_extractor(field)
                extractors.append(
                    extractor_cls(self.test_case, field_token, self.model_interface, field, self.document)
                )

            self._extractors = extractors
        return self._extractors


class ModelFactoryConverter(ModelConverter):
    """
    This converter will convert a document into a model factory statement and everything that belongs to it.
    """
    def prepare_statements(self, statements):
        """
        Before working with the extractors, create an assignment statement with the model factory. That statement
        will be used to add the values of the extractors.
        """
        expression = ModelFactoryExpression(model_interface=self.model_interface, factory_kwargs=[])
        variable = Variable(
            name_predetermined=self.variable_name,
            reference_string=self.variable_reference_string,
        )
        statement = AssignmentStatement(variable=variable, expression=expression)
        return [statement]

    def get_document_compatibility(self):
        compatibility = 1

        if isinstance(self.model_interface, AbstractModelInterface):
            compatibility *= 0.8

        # models are normally displayed by nouns
        if not token_is_noun(self.model_token):
            compatibility *= 0.01

        # If the root of the document is a finites Modalverb (e.g. sollte) it is rather unlikely that the creation of
        # a model is meant
        root = get_root_of_token(self.model_token)
        if root and root.tag_ == 'VMFIN':
            compatibility *= 0.4

        return compatibility

    def handle_extractor(self, extractor, statements):
        """
        For each extractor, get the factory statement that was created in `prepare_statements`. After that
        extract the value from the extractor and add it an a Kwarg to the factory.
        """
        super().handle_extractor(extractor, statements)
        factory_kwargs = statements[0].expression.function_kwargs

        extracted_value = extractor.extract_value()
        if extracted_value is None:
            return

        kwarg = Kwarg(extractor.field_name, extracted_value)
        factory_kwargs.append(kwarg)

    def get_statements_from_datatable(self):
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


class ModelVariableReferenceConverter(ModelConverter):
    """
    This converter is used in cases where steps simply reference other steps where a variable was defined:
        - Given a user Alice ...
        - And Alice has a password "Haus1234"
    """
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
        """Returns the variable token that holds the model instance that will be changed."""
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
        """Returns the variable that is referenced by the document and where fields should be changed."""
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
        """Returns the model interface for this converter."""
        # if the referenced variable was found, return the model of that variable
        if self._referenced_variable is not None and self._referenced_variable_determined:
            self._model = self._referenced_variable.value.model_interface
            return self._model

        if self._model_determined is False:
            model_searcher = ModelSearcher(text=str(self.model_token.lemma_), src_language=self.language)
            model = None

            # try to search for a model
            try:
                found_m_interface = model_searcher.search(project_interface=self.django_project, raise_exception=True)
            except NoConversionFound:
                found_m_interface = None

            # try to find a statement where the found model is saved in the expression
            if found_m_interface:
                for statement in self.test_case.statements:
                    exp = statement.expression
                    if isinstance(exp, ModelFactoryExpression) and found_m_interface.model == exp.model_interface.model:
                        model = found_m_interface
                        break

            self._model_determined = True
            self._model = model
        return self._model

    def handle_extractor(self, extractor, statements):
        """Each value that was extracted represents a statement in which the value is set on the model instance."""
        variable = self.referenced_variable
        argument = Argument(value=extractor.extract_value())

        statement = ModelFieldAssignmentStatement(
            variable=variable,
            assigned_value=argument,
            field_name=extractor.field_name,
        )
        statements.append(statement)

    def get_statements_from_extractors(self, extractors):
        """At the end there has to be a `save` call."""
        statements = super().get_statements_from_extractors(extractors)
        statements.append(ModelSaveExpression(self.referenced_variable).as_statement())
        return statements


class RequestConverter(Converter):
    @property
    def extractors(self):
        UrlSearcher(str(self.document), self.language, self.django_project).search()
        return []
