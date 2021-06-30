from django_meta.model import AbstractModelAdapter
from nlp.converter.base.converter import Converter
from nlp.converter.property import NewModelProperty, NewVariableProperty, ReferenceVariableProperty, \
    ReferenceModelProperty, UserReferenceVariableProperty, ModelWithUserProperty, \
    MethodProperty
from nlp.extractor import get_model_field_extractor, ModelFieldExtractor
from nlp.generate.argument import Kwarg, Argument
from nlp.generate.expression import ModelFactoryExpression, ModelSaveExpression
from nlp.generate.statement import AssignmentStatement, ModelFieldAssignmentStatement
from nlp.searcher import ModelFieldSearcher, NoConversionFound, UrlSearcher
from nlp.utils import get_non_stop_tokens, get_noun_chunk_of_token, token_is_noun, get_root_of_token, \
    NoToken


class ModelConverter(Converter):
    def __init__(self, document, related_object, django_project, test_case):
        super().__init__(document, related_object, django_project, test_case)
        self._extractors = None
        self._fields = None
        self.model = NewModelProperty(self)
        self.variable = NewVariableProperty(self)

    def _search_for_field(self, span, token):
        """
        Searches for a field with a given span and token inside the self.model_adapter
        """
        # all the following nouns will reference fields of that model, so find a field
        if span:
            field_searcher_span = ModelFieldSearcher(text=str(span), src_language=self.language)

            try:
                return field_searcher_span.search(raise_exception=True, model_adapter=self.model.value)
            except NoConversionFound:
                pass

            field_searcher_root = ModelFieldSearcher(text=str(span.root.lemma_), src_language=self.language)
            try:
                return field_searcher_root.search(
                    raise_exception=bool(token), model_adapter=self.model.value)
            except NoConversionFound:
                pass

        if token:
            field_searcher_token = ModelFieldSearcher(text=str(token), src_language=self.language)
            return field_searcher_token.search(model_adapter=self.model.value)

        return None

    @property
    def fields(self):
        """Returns all the fields that the document references."""
        if self.model.value is None:
            return []

        if self._fields is None:
            fields = []

            for token in get_non_stop_tokens(self.document):
                if token == self.model.token or self.variable.token == token:
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
                    extractor_cls(self.test_case, field_token, self.model.value, field, self.document)
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
        expression = ModelFactoryExpression(model_adapter=self.model.value, factory_kwargs=[])
        variable = self.variable.value
        statement = AssignmentStatement(variable=variable, expression=expression)
        return [statement]

    def get_document_compatibility(self):
        compatibility = 1

        if isinstance(self.model.value, AbstractModelAdapter):
            compatibility *= 0.8

        # models are normally displayed by nouns
        if not token_is_noun(self.model.token):
            compatibility *= 0.01

        # If the root of the document is a finites Modalverb (e.g. sollte) it is rather unlikely that the creation of
        # a model is meant
        root = get_root_of_token(self.model.token)
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
                field = field_searcher.search(model_adapter=self.model.value)
                extractors_copy.append(
                    ModelFieldExtractor(
                        test_case=self.test_case,
                        model_adapter=self.model.value,
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
        self.variable = ReferenceVariableProperty(self)
        self.model = ReferenceModelProperty(self)

    def get_document_compatibility(self):
        if self.variable.value:
            return 1
        return 0

    def handle_extractor(self, extractor, statements):
        """Each value that was extracted represents a statement in which the value is set on the model instance."""
        statement = ModelFieldAssignmentStatement(
            variable=self.variable.value,
            assigned_value=Argument(value=extractor.extract_value()),
            field_name=extractor.field_name,
        )
        statements.append(statement)

    def get_statements_from_extractors(self, extractors):
        """At the end there has to be a `save` call."""
        statements = super().get_statements_from_extractors(extractors)
        statements.append(ModelSaveExpression(self.variable.value).as_statement())
        return statements


class RequestConverter(Converter):
    """
    This converter is responsible to turn a document into statements that will do a request to the django REST api.
    """
    def __init__(self, document, related_object, django_project, test_case):
        super().__init__(document, related_object, django_project, test_case)
        self._url_pattern_adapter = None

        self.user = UserReferenceVariableProperty(self)
        self.model = ModelWithUserProperty(self)
        self.method = MethodProperty(self)

    def get_document_compatibility(self):
        if not self.method.token:
            return 0
        return 1

    @property
    def from_anonymous_user(self):
        return isinstance(self.user.token, NoToken)

    @property
    def url_pattern_adapter(self):
        if self._url_pattern_adapter is None:
            searcher = UrlSearcher(str(self.method.token), self.language, self.model.value, [self.method])
            self._url_pattern_adapter = searcher.search(self.django_project)
        return self._url_pattern_adapter

    @property
    def extractors(self):
        a = self.method.token
        b = self.url_pattern_adapter
        return []
