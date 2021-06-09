from django.forms import CharField, IntegerField, BooleanField

from generate.suite import AssignmentStatement, ModelFactoryExpression, Kwarg
from generate.utils import to_function_name
from nlp.django import TextToModelConverter, TextToModelFieldConverter, NoConversionFound
from nlp.setup import Nlp
from nlp.utils import get_noun_chunks, token_references, get_referenced_entity


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

        # TODO: handle other fields than CharField
        for field_name, token, field in field_values:
            as_variable = test_case.variable_defined(to_function_name(str(token)))
            value = to_function_name(str(token)) if as_variable else str(token)
            factory_kwargs.append(Kwarg(field_name, value, as_variable=as_variable))

        factory_statement = ModelFactoryExpression(model, factory_kwargs)
        return AssignmentStatement(factory_statement, self.get_assignment_text(model_noun_token))

    def token_references_noun(self, token, noun):
        return token_references(token, noun) and token.pos_ == 'PROPN'

    def get_assignment_text(self, root_noun):
        try:
            next_token = self.document[root_noun.i + 1]
        except IndexError:
            return None

        if self.token_references_noun(next_token, root_noun):
            return to_function_name(str(next_token))

        for named_entity in self.document.ents:
            for token in named_entity:
                if token_references(token, root_noun):
                    return to_function_name(str(token))

        return None

    def get_statements(self, test_case):
        model = None
        model_noun_token = None
        field_values = []
        unhandled_propn = None

        for index, noun_chunk in enumerate(get_noun_chunks(self.document)):
            root_noun = str(noun_chunk.root)

            # first the model for an object is defined
            if index == 0:
                model_noun_token = noun_chunk.root
                model_converter = TextToModelConverter(text=root_noun, src_language=self.language)
                model = model_converter.convert(project_interface=self.django_project)
                continue

            # filter out any noun chunks without a noun
            if noun_chunk.root.pos_ != 'NOUN':
                # if it is a proper noun, it will be handled later
                if noun_chunk.root.pos_ == 'PROPN':
                    unhandled_propn = noun_chunk.root
                continue

            # all the following nouns will reference fields of that model, so find a field
            field_converter_span = TextToModelFieldConverter(text=str(noun_chunk), src_language=self.language)

            # try to find something for whole span first
            try:
                field = field_converter_span.convert(model_interface=model, raise_exception=True)
            # if nothing is found, try the root instead
            except NoConversionFound:
                field_converter_root = TextToModelFieldConverter(text=root_noun, src_language=self.language)
                field = field_converter_root.convert(model_interface=model)

            field_name = field.name

            # search for any tokens that reference the root element - which means that they contain the value for
            # that field
            field_value = None
            for token in noun_chunk:
                if self.token_references_noun(token, noun_chunk.root):
                    field_value = token
                    break

            if field_value is None and unhandled_propn is None:
                continue

            if field_value is None:
                field_value = unhandled_propn
                unhandled_propn = None

            field_values.append((field_name, field_value, field))

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
                field = field_converter.convert(model_interface=model)
                field_name = field.name
                field_values_copy.append((field_name, cell.value, field))

            statements.append(self.create_statement(field_values_copy, test_case, model, model_noun_token))

        return statements
