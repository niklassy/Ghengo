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
    def get_assignment_text(self, root_noun):
        for named_entity in self.document.ents:
            for token in named_entity:
                if token.head == root_noun:
                    return to_function_name(str(token))

        return 'asd'

    def get_statements(self, test_case):
        noun_chunks = get_noun_chunks(self.document)
        model = None
        field_values = []
        root_noun_token = None

        for index, noun_chunk in enumerate(noun_chunks):
            root_noun = str(noun_chunk.root)

            # first the model for an object is defined
            if index == 0:
                root_noun_token = noun_chunk.root
                model_converter = TextToModelConverter(text=root_noun, src_language=self.language)

                try:
                    model = model_converter.convert(project_interface=self.django_project)
                except NoConversionFound:
                    model = AbstractModelInterface(name=root_noun)
                continue

            field_converter = TextToModelFieldConverter(text=root_noun, src_language=self.language)
            try:
                field = field_converter.convert(model_interface=model)
                field_name = field.name
            except NoConversionFound:
                field_name = to_function_name(root_noun)

            value = None
            # search for any tokens that reference the root element
            for token in noun_chunk:
                if token.head == noun_chunk.root:
                    value = token

            if value is None:
                continue

            field_values.append((field_name, value))

        factory_kwargs = []
        for field_name, token in field_values:
            token_as_str = str(token)
            as_variable = test_case.variable_defined(token_as_str)
            factory_kwargs.append(Kwarg(field_name, token_as_str, as_variable=as_variable))

        factory_statement = ModelFactoryExpression(model, factory_kwargs)
        statement = AssignmentStatement(factory_statement, self.get_assignment_text(root_noun_token))

        return [statement]
