from django.apps import apps
from django.conf.global_settings import AUTH_USER_MODEL

from django_meta.model import ModelAdapter, AbstractModelAdapter
from nlp.converter.base_property import ConverterProperty
from nlp.generate.expression import ModelFactoryExpression
from nlp.generate.variable import Variable
from nlp.locator import RestActionLocator, FileLocator
from nlp.searcher import ModelSearcher, NoConversionFound
from nlp.utils import token_to_function_name, NoToken, is_proper_noun_of, token_is_proper_noun, is_quoted, \
    token_is_noun, token_is_like_num, get_next_token, get_all_children


class NewModelProperty(ConverterProperty):
    """This property can be used to get the chunk, token and value to create a new model instance."""
    def __init__(self, converter, blocked_tokens=None):
        super().__init__(converter)

        if blocked_tokens is None:
            self.blocked_tokens = []
        else:
            self.blocked_tokens = blocked_tokens

    def get_chunk(self):
        for chunk in self.converter.get_noun_chunks():
            if any([token_is_noun(t) and t not in self.blocked_tokens for t in chunk]):
                return chunk

        return None

    def get_token(self):
        return self.chunk.root if self.chunk else NoToken()

    def get_value(self):
        if not self.token:
            return None

        searcher = ModelSearcher(text=str(self.token.lemma_), src_language=self.converter.language)
        return searcher.search(project_adapter=self.converter.django_project)


class ModelCountProperty(NewModelProperty):
    """
    This property refers to a number of models. So `2 orders` or `seven users`.
    """
    def get_token(self):
        model_token = self.converter.model.token

        if not model_token:
            return NoToken()

        for child in get_all_children(model_token):
            if child.i >= model_token.i:
                continue

            if child.is_digit or token_is_like_num(child):
                return child

        return NoToken()

    def get_value(self):
        return str(self.token)


class NewVariableProperty(ConverterProperty):
    def get_chunk(self):
        if len(self.converter.get_noun_chunks()) == 0:
            return None

        return self.converter.get_noun_chunks()[0]

    def variable_defined_in_test_case(self, token, reference_string):
        """Returns if the test case has the variable defined that is determined by the token and the reference str."""
        future_name = token_to_function_name(token)
        return self.converter.test_case.variable_defined(future_name, reference_string)

    def get_related_object_property(self):
        raise NotImplementedError()

    @property
    def reference_string(self):
        """Returns the reference string that is passed to the variable of this document."""
        related_property = self.get_related_object_property()

        return related_property.value.name if related_property.value else ''

    def get_token(self):
        """
        Returns the token that represents the variable. Because this is a completely new variable, try to search
        for variables that are digits or proper nouns that are NOT defined as a variable yet.
        """
        for child in self.get_token_possibilities():
            variable_in_tc = self.variable_defined_in_test_case(child, self.reference_string)

            # sometimes nlp gets confused about variables and what belongs to this model factory and
            # what is a reference to an older variable - so if there is a variable with the exact same name
            # we assume that that token is not valid
            propn_or_digit = child.is_digit or is_proper_noun_of(child, self.get_related_object_property().token)
            if (propn_or_digit or is_quoted(child)) and not variable_in_tc:
                return child

        return NoToken()

    def get_token_possibilities(self):
        """Returns an Iterable of all Tokens that are possible as a value."""
        related_token = self.get_related_object_property().token

        if not related_token:
            return []

        # get all related children but skip those that come before the actual token, the variables are usually
        # defined AFTER the related token `given a user Alice`, `Given an order 1`
        related_children = [child for child in related_token.children if child.i > related_token.i]

        # check the token afterwards too in case NLP does not recognize `1` as a child
        after_model_token = get_next_token(related_token)
        if not after_model_token:
            return related_children

        possibilities = related_children + [after_model_token]

        # filter out any values in quotes that is not coming rights after the related token
        return [t for t in possibilities if not (is_quoted(t) and t != after_model_token)]

    def get_value(self):
        """The output will be a variable instance."""
        return Variable(name_predetermined=self.name, reference_string=self.reference_string)

    @property
    def name(self):
        """The name of the variable."""
        return token_to_function_name(self.token)


class NewModelVariableProperty(NewVariableProperty):
    """This property can be used to get extract the data to create a new variable."""
    def get_related_object_property(self):
        return self.converter.model


class NewFileVariableProperty(NewVariableProperty):
    def get_related_object_property(self):
        return self.converter.file

    def get_token_possibilities(self):
        """The variable cannot be represented by the token that represents the file extension."""
        possibilities = super().get_token_possibilities()
        return [token for token in possibilities if token != self.converter.file_extension_locator.fittest_token]


class ReferenceModelVariableProperty(NewModelVariableProperty):
    """
    This property can be used when a variable is needed that was already created previously.
    """
    def get_token_possibilities(self):
        """Since we are referencing a variable, try the model token children and the own chunk."""
        return [c for c in self.converter.model.token.children] + [t for t in self.chunk]

    def get_model_adapter(self, statement):
        """
        Returns the model of the variable. By default it tries to access the model in the converter. If that
        is not available, use the model from the statement.
        """
        if hasattr(self.converter, 'model'):
            model_adapter = self.get_related_object_property().value

            # if the found model is abstract, use the adapter from the statement, just to be sure
            if model_adapter.__class__ == AbstractModelAdapter:
                return statement.expression.model_adapter

            return self.converter.model.value or statement.expression.model_adapter
        return statement.expression.model_adapter

    def get_token(self):
        """The token of the variable must reference a variable that was previously defined."""
        if not self.chunk:
            return NoToken()

        for statement in self.converter.test_case.statements:
            if not isinstance(statement.expression, ModelFactoryExpression):
                continue

            model_adapter = self.get_model_adapter(statement)
            if not model_adapter or model_adapter.model != statement.expression.model_adapter.model:
                continue

            for token in self.get_token_possibilities():
                defined_in_tc = self.variable_defined_in_test_case(token, model_adapter.name)
                if (token.is_digit or token_is_proper_noun(token) or is_quoted(token)) and defined_in_tc:
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
        if not self.token:
            return None

        for statement in self.converter.test_case.statements:
            if not isinstance(statement.expression, ModelFactoryExpression):
                continue

            model = self.get_model_adapter(statement)
            future_name = token_to_function_name(self.token)

            if statement.string_matches_variable(future_name, model.name):
                return statement.variable.copy()

        return None


class ReferenceModelProperty(NewModelProperty):
    """
    This property can be used for cases where the model can be defined indirectly by referencing a variable that
    was created earlier in the test case.
    """
    def get_chunk(self):
        if len(self.converter.get_noun_chunks()) == 0:
            return None

        return self.converter.get_noun_chunks()[0]

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


class UserReferenceVariableProperty(ReferenceModelVariableProperty):
    """
    This property can be used when a variable is referenced from the model User.
    """
    def get_model_adapter(self, statement):
        user_path = AUTH_USER_MODEL.split('.')

        return ModelAdapter.create_with_model(
            apps.get_model(user_path[0], user_path[1])
        )

    def get_token_possibilities(self):
        """In this case, the user is the model, so search for the token in the own chunk only."""
        return self.chunk


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


class FileProperty(ConverterProperty):
    def __init__(self, converter):
        super().__init__(converter)
        self.locator = FileLocator(self.document)
        self.locator.locate()

    def get_chunk(self):
        if len(self.converter.get_noun_chunks()) == 0:
            return None

        return self.converter.get_noun_chunks()[0]

    def get_value(self):
        """In this case the file name is returned."""
        return None

    def get_token(self):
        return self.locator.fittest_token
