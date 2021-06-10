from generate.suite import AssignmentStatement, ModelFactoryExpression, Kwarg
from generate.utils import to_function_name
from nlp.determiner import FieldValueDeterminer, SpanFieldValueDeterminer, TokenFieldValueDeterminer, \
    StringFieldValueDeterminer
from nlp.searcher import ModelSearcher, ModelFieldSearcher, NoConversionFound
from nlp.setup import Nlp
from nlp.utils import get_noun_chunks, token_references, is_proper_noun_of


class GherkinToCodeConverter(object):
    def __init__(self, ast_object, language, django_project):
        self.ast_object = ast_object
        self.language = language
        self._document = None
        self.django_project = django_project

    @property
    def ast_as_text(self):
        return str(self.ast_object)

    @property
    def document(self):
        if self._document is None:
            self._document = Nlp.for_language(self.language)(self.ast_as_text)
        return self._document

    def get_statements(self, test_case):
        raise NotImplementedError()


class GivenToCodeConverter(GherkinToCodeConverter):
    def __init__(self, ast_object, language, django_project):
        super().__init__(ast_object, language, django_project)
        self.model = None
        self._field_values = []

    def create_statement(self, determiners: [FieldValueDeterminer], test_case):
        factory_kwargs = []

        for determiner in determiners:
            valid_fn = determiner.value_can_be_function_name()
            python_value = determiner.value_to_python()
            as_variable = valid_fn and test_case.variable_defined(to_function_name(python_value))
            value = to_function_name(python_value) if as_variable else python_value
            factory_kwargs.append(Kwarg(determiner.field_name, value, as_variable=as_variable))

        factory_statement = ModelFactoryExpression(self.model, factory_kwargs)
        return AssignmentStatement(factory_statement, self.get_assignment_text(self.model_noun_token))

    def get_assignment_text(self, root_noun):
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

    def get_noun_chunks(self):
        return get_noun_chunks(self.document)

    def _initialize_model(self):
        """
        Find the model for the given statement and save data so that it can be accessed later.

        The model can be found in the first chunk:
            => Gegeben sei ein Benutzer ...
            => Given a user ...
        """
        self.model = None
        noun_chunks = self.get_noun_chunks()
        model_noun_chunk = noun_chunks[0]
        self.model_noun_token = model_noun_chunk.root
        model_searcher = ModelSearcher(text=str(self.model_noun_token), src_language=self.language)
        self.model = model_searcher.search(project_interface=self.django_project)

    def _initialize_fields(self):
        self._field_values = []
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
                field = field_searcher_span.search(raise_exception=True, model_interface=self.model)
            # if nothing is found, try the root instead
            except NoConversionFound:
                field_searcher_root = ModelFieldSearcher(text=str(noun_chunk.root), src_language=self.language)
                field = field_searcher_root.search(model_interface=self.model)

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
                self._field_values.append(TokenFieldValueDeterminer(self.model, unhandled_propn, field))
            else:
                self._field_values.append(SpanFieldValueDeterminer(self.model, noun_chunk, field))

    def get_statements(self, test_case):
        self._initialize_model()
        self._initialize_fields()

        if not self.ast_object.has_datatable:
            return [self.create_statement(self._field_values, test_case)]

        # if the given has a datatable, it is assumed that it contains data to create model entries
        # if this is the case, add more field values to the model creation
        datatable = self.ast_object.argument
        column_names = datatable.get_column_names()
        statements = []

        for row in datatable.rows:
            field_values_copy = self._field_values.copy()

            for index, cell in enumerate(row.cells):
                field_searcher = ModelFieldSearcher(column_names[index], src_language=self.language)
                field = field_searcher.search(model_interface=self.model)
                field_values_copy.append(StringFieldValueDeterminer(self.model, cell.value, field))

            statements.append(self.create_statement(field_values_copy, test_case))

        return statements
