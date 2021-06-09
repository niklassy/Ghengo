from django_meta.project import AbstractModelInterface
from generate.suite import AssignmentStatement, ModelFactoryExpression, Kwarg
from generate.utils import to_function_name
from nlp.django import TextToModelConverter, NoConversionFound, TextToModelFieldConverter
from nlp.setup import Nlp
from nlp.utils import get_noun_chunks


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
    def create_statement(self, field_values, test_case, model, model_noun_token):
        factory_kwargs = []
        for field_name, token in field_values:
            token_as_str = str(token)
            as_variable = test_case.variable_defined(token_as_str)
            factory_kwargs.append(Kwarg(field_name, token_as_str, as_variable=as_variable))

        factory_statement = ModelFactoryExpression(model, factory_kwargs)
        return AssignmentStatement(factory_statement, self.get_assignment_text(model_noun_token))

    def get_assignment_text(self, root_noun):
        try:
            next_token = self.document[root_noun.i + 1]
        except IndexError:
            return None

        if next_token.head == root_noun and next_token.pos_ == 'PROPN':
            return to_function_name(str(next_token))

        for named_entity in self.document.ents:
            for token in named_entity:
                if token.head == root_noun:
                    return to_function_name(str(token))

        return None

    def get_statements(self, test_case):
        noun_chunks = get_noun_chunks(self.document)
        model = None
        field_values = []
        model_noun_token = None

        for index, noun_chunk in enumerate(noun_chunks):
            root_noun = str(noun_chunk.root)

            # first the model for an object is defined
            if index == 0:
                model_noun_token = noun_chunk.root
                model_converter = TextToModelConverter(text=root_noun, src_language=self.language)
                model = model_converter.convert(project_interface=self.django_project)

            # all the following nouns will reference fields of that model, so find a field
            field_converter = TextToModelFieldConverter(text=root_noun, src_language=self.language)
            field_name = field_converter.convert(model_interface=model).name

            # search for any tokens that reference the root element - which means that they contain the value for
            # that field
            field_value = None
            for token in noun_chunk:
                if token.head == noun_chunk.root:
                    field_value = token

            if field_value is None:
                continue

            field_values.append((field_name, field_value))

        if not self.ast_object.has_datatable:
            return [self.create_statement(field_values, test_case, model, model_noun_token)]

        # if the given has a datatable, it is assumed that it contains data to create model entries
        # if this is the case, add more field values to the model creation
        datatable = self.ast_object.argument
        column_names = datatable.get_column_names()
        statements = []

        for row in datatable.rows:
            field_values_copy = field_values.copy()

            for index, cell in enumerate(row.cells):
                field_converter = TextToModelFieldConverter(column_names[index], src_language=self.language)
                field_name = field_converter.convert(model_interface=model).name
                field_values_copy.append((field_name, cell.value))

            statements.append(self.create_statement(field_values_copy, test_case, model, model_noun_token))

        return statements
