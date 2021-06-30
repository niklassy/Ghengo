from django.apps import apps
from django.conf.global_settings import AUTH_USER_MODEL

from django_meta.model import ModelAdapter
from nlp.converter.base.property import ConverterProperty
from nlp.generate.expression import ModelFactoryExpression
from nlp.generate.variable import Variable
from nlp.locator import RestActionLocator
from nlp.searcher import ModelSearcher, NoConversionFound
from nlp.utils import token_to_function_name, NoToken, is_proper_noun_of, token_is_proper_noun


class NewModelProperty(ConverterProperty):
    """This property can be used to get the chunk, token and value to create a new model instance."""
    def get_chunk(self):
        return self.converter.get_noun_chunks()[0]

    def get_token(self):
        return self.chunk.root

    def get_value(self):
        searcher = ModelSearcher(text=str(self.token.lemma_), src_language=self.converter.language)
        return searcher.search(project_adapter=self.converter.django_project)


class NewVariableProperty(ConverterProperty):
    """This property can be used to get extract the data to create a new variable."""
    def get_chunk(self):
        return self.converter.get_noun_chunks()[0]

    def variable_defined_in_test_case(self, token, reference_string):
        """Returns if the test case has the variable defined that is determined by the token and the reference str."""
        future_name = token_to_function_name(token)
        return self.converter.test_case.variable_defined(future_name, reference_string)

    @property
    def reference_string(self):
        """Returns the reference string that is passed to the variable of this document."""
        return self.converter.model.value.name

    def get_token(self):
        """
        Returns the token that represents the variable. Because this is a completely new variable, try to search
        for variables that are digits or proper nouns that are NOT defined as a variable yet.
        """
        for child in self.converter.model.token.children:
            variable_in_tc = self.variable_defined_in_test_case(child, self.reference_string)

            # sometimes nlp gets confused about variables and what belongs to this model factory and
            # what is a reference to an older variable - so if there is a variable with the exact same name
            # we assume that that token is not valid
            if (child.is_digit or is_proper_noun_of(child, self.converter.model.token)) and not variable_in_tc:
                return child

        return NoToken()

    @property
    def name(self):
        """The name of the variable."""
        return token_to_function_name(self.token)

    def get_value(self):
        """The output will be a variable instance."""
        return Variable(name_predetermined=self.name, reference_string=self.reference_string)


class ReferenceVariableProperty(NewVariableProperty):
    """
    This property can be used when a variable is needed that was already created previously.
    """
    def get_model_adapter(self, statement):
        """
        Returns the model of the variable. By default it tries to access the model in the converter. If that
        is not available, use the model from the statement.
        """
        if hasattr(self.converter, 'model'):
            return self.converter.model.value or statement.expression.model_adapter
        return statement.expression.model_adapter

    def get_token(self):
        """The token of the variable must reference a variable that was previously defined."""
        for statement in self.converter.test_case.statements:
            if not isinstance(statement.expression, ModelFactoryExpression):
                continue

            model = self.get_model_adapter(statement)

            for token in self.chunk:
                defined_in_tc = self.variable_defined_in_test_case(token, model.name)
                if (token.is_digit or token_is_proper_noun(token)) and defined_in_tc:
                    return token

        return NoToken()

    @property
    def name(self):
        """The name of the variable will be accessed from the variable name."""
        return self.value.name if self.value else ''

    def get_value(self):
        """
        Because this references a variable that is already defined in the test case, go over each statement and try
        to find a variable that matches the model and the function name of the token.
        """
        variable_token = self.token

        if not variable_token:
            return None

        for statement in self.converter.test_case.statements:
            if not isinstance(statement.expression, ModelFactoryExpression):
                continue

            model = self.get_model_adapter(statement)
            future_name = token_to_function_name(variable_token)

            if statement.string_matches_variable(future_name, model.name):
                return statement.variable.copy()

        return None


class ReferenceModelProperty(NewModelProperty):
    """
    This property can be used for cases where the model can be defined indirectly by referencing a variable that
    was created earlier in the test case.
    """
    @property
    def value(self):
        """
        In sentences like "Alice does ..." we don't know the model of alice initially. So if the variable of
        the converter is found, we can use the variable model instead.
        """
        if self.converter.variable.value_determined is True and self.converter.variable.value is not None:
            variable = self.converter.variable.value
            return variable.value.model_adapter

        return super().value

    def get_value(self):
        """
        Try to find a model from the token. If none is found return None instead of a placeholder. Also
        try to find the model in a previous statement.
        """
        model_searcher = ModelSearcher(text=str(self.token.lemma_), src_language=self.converter.language)

        # try to search for a model
        try:
            found_m_adapter = model_searcher.search(
                project_adapter=self.converter.django_project, raise_exception=True)
        except NoConversionFound:
            return None

        # try to find a statement where the found model is saved in the expression
        for statement in self.converter.test_case.statements:
            exp = statement.expression
            if isinstance(exp, ModelFactoryExpression) and found_m_adapter.model == exp.model_adapter.model:
                return found_m_adapter

        return None


class UserReferenceVariableProperty(ReferenceVariableProperty):
    """
    This property can be used when a variable is referenced from the model User.
    """
    def get_model_adapter(self, statement):
        user_path = AUTH_USER_MODEL.split('.')

        return ModelAdapter.create_with_model(
            apps.get_model(user_path[0], user_path[1])
        )


class ModelWithUserProperty(NewModelProperty):
    """
    This property can be used if there is a model defined beside a user:

    E.g. Alice creates an Order
    """
    def get_chunk(self):
        """
        The model is contained in the chunk that does not hold the user or the method.
        """
        method_token_chunk = None

        for chunk in self.converter.get_noun_chunks():
            # in some cases the chunk might be the same as the method chunk (e.g. `Alice gets the order list`)
            if self.converter.method.token in chunk:
                method_token_chunk = chunk

            if self.converter.user.token not in chunk and self.converter.method.token not in chunk:
                return chunk

        return method_token_chunk


class MethodProperty(ConverterProperty):
    """
    The method property can be used to find a REST method in a sentence.
    """
    def __init__(self, converter):
        super().__init__(converter)
        self.locator = RestActionLocator(self.document)
        self.locator.locate()

    def get_value(self):
        return self.locator.method

    def get_token(self):
        return self.locator.fittest_token

    def get_chunk(self):
        return None
