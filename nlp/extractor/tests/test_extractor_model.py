import pytest

from core.constants import Languages
from django_meta.model import ModelFieldWrapper, ExistingModelWrapper, ModelWrapper, ExistingModelFieldWrapper
from django_meta.project import DjangoProject
from nlp.extractor.fields_model import ModelFieldExtractor, IntegerModelFieldExtractor, FloatModelFieldExtractor, \
    BooleanModelFieldExtractor, ForeignKeyModelFieldExtractor, M2MModelFieldExtractor
from nlp.generate.argument import Kwarg
from nlp.generate.expression import ModelM2MAddExpression
from nlp.generate.pytest import PyTestModelFactoryExpression
from nlp.generate.pytest.suite import PyTestTestSuite
from nlp.generate.statement import AssignmentStatement
from nlp.generate.variable import Variable, VariableReference
from nlp.generate.warning import GenerationWarning
from nlp.setup import Nlp

suite = PyTestTestSuite('bar')
default_test_case = suite.create_and_add_test_case('foo')
model_wrapper = ModelWrapper('Order')
field = ModelFieldWrapper('name')
nlp = Nlp.for_language(Languages.DE)
document = nlp('Sie hat 3 Äpfel.')


@pytest.mark.parametrize(
    'value, expected_value', [
        ('1', 1),
        ('Wahr', True),
        ('False', False),
        ('falsch', False),
        ('0.33', 0.33),
        ('Some string', 'Some string'),
        ('"Some string"', 'Some string'),
        ('\'Some string\'', 'Some string'),
    ]
)
def test_model_field_extractor_extract_string(value, expected_value):
    """Check that the model field extractor can still handle strings as source."""
    extractor = ModelFieldExtractor(default_test_case, value, model_wrapper, field, document)
    assert extractor.extract_value() == expected_value
    assert type(extractor.extract_value()) == type(expected_value)


def test_model_field_extractor_extract_char():
    """Check if the model field extractor handles different cases in documents correctly."""
    test_case = suite.create_and_add_test_case('qweqwe')

    # check normal string
    doc = nlp('Gegeben sei ein Benutzer mit dem Namen Alice')
    extractor = ModelFieldExtractor(test_case, doc[6], model_wrapper, field, doc)
    assert extractor.extract_value() == 'Alice'

    # check stirng with quotations
    doc = nlp('Gegeben sei ein Benutzer mit dem Namen "Alice"')
    extractor = ModelFieldExtractor(test_case, doc[6], model_wrapper, field, doc)
    assert extractor.extract_value() == 'Alice'

    # check bool true
    doc = nlp('Gegeben sei ein aktiver Benutzer')
    extractor = ModelFieldExtractor(test_case, doc[3], model_wrapper, field, doc)
    assert extractor.extract_value() is True

    # check bool False
    doc = nlp('Gegeben sei ein nicht aktiver Benutzer')
    extractor = ModelFieldExtractor(test_case, doc[4], model_wrapper, field, doc)
    assert extractor.extract_value() is False

    # check int
    doc = nlp('Gegeben sei ein nicht aktiver Benutzer mit dem Namen Alice und dem Rang 7')
    extractor = ModelFieldExtractor(test_case, doc[12], model_wrapper, field, doc)
    assert extractor.extract_value() == 7

    # check float
    doc = nlp('Gegeben sei ein nicht aktiver Benutzer mit dem Namen Alice und dem Rang 7.987123')
    extractor = ModelFieldExtractor(test_case, doc[12], model_wrapper, field, doc)
    assert extractor.extract_value() == 7.987123

    # check variable that is referenced
    test_case.add_statement(AssignmentStatement(
        expression=PyTestModelFactoryExpression(model_wrapper, [Kwarg('bar', 123)]),
        variable=Variable('Bob', 'Order'),      # <-- variable defined
    ))
    doc = nlp('Gegeben sei ein Benutzer mit dem Auftrag Bob')   # <-- Bob references that variable
    extractor = ModelFieldExtractor(test_case, doc[6], model_wrapper, field, doc)
    assert isinstance(extractor.extract_value(), VariableReference)
    assert extractor.extract_value().name == 'bob'


def test_model_field_extractor_extract_number():
    """Checks if the number is correctly extracted."""
    from django_sample_project.apps.order.models import ToDo

    doc = nlp('Gegeben sei ein Todo aus dem System 3')
    extractor = IntegerModelFieldExtractor(
        test_case=default_test_case,
        source=doc[6],
        model_wrapper=model_wrapper,
        field_wrapper=ExistingModelFieldWrapper(ToDo._meta.get_field('system')),
        document=doc
    )
    assert extractor.extract_value() == 3
    extractor_2 = ModelFieldExtractor(
        test_case=default_test_case,
        source='3',
        model_wrapper=model_wrapper,
        field_wrapper=ExistingModelFieldWrapper(field),
        document=document
    )
    assert extractor_2.extract_value() == 3


def test_model_field_extractor_extract_float():
    """Checks if the float is correctly extracted."""
    from django_sample_project.apps.order.models import ToDo
    float_field = ExistingModelFieldWrapper(ToDo._meta.get_field('part'))

    # check if quotation marks are handled as wanted
    doc = nlp('Gegeben sei ein Todo aus dem Teil "0.33"')
    extractor = FloatModelFieldExtractor(default_test_case, doc[6], model_wrapper, float_field, doc)
    assert extractor.extract_value() == 0.33

    # is string still handled?
    extractor_2 = FloatModelFieldExtractor(default_test_case, '0.33', model_wrapper, float_field, doc)
    assert extractor_2.extract_value() == 0.33

    # in some cases the nlp has trouble finding the float, so if thats the case, there should be a warning
    doc = nlp('Gegeben sei ein Todo aus dem Teil 0.33')
    extractor_3 = FloatModelFieldExtractor(default_test_case, doc[6], model_wrapper, float_field, doc)
    assert isinstance(extractor_3.extract_value(), GenerationWarning)


def test_model_field_extractor_extract_boolean():
    """Checks if the boolean is correctly extracted."""
    from django_sample_project.apps.order.models import ToDo
    bool_field = ExistingModelFieldWrapper(ToDo._meta.get_field('from_other_system'))

    doc = nlp('Gegeben sei ein Todo, das aus dem anderen System kommt')
    extractor = BooleanModelFieldExtractor(default_test_case, doc[9], model_wrapper, bool_field, doc)
    assert extractor.extract_value() is True
    doc = nlp('Gegeben sei ein Todo, das nicht aus dem anderen System kommt')
    extractor = BooleanModelFieldExtractor(default_test_case, doc[10], model_wrapper, bool_field, doc)
    assert extractor.extract_value() is False
    extractor = BooleanModelFieldExtractor(default_test_case, 'false', model_wrapper, bool_field, doc)
    assert extractor.extract_value() is False
    extractor = BooleanModelFieldExtractor(default_test_case, '0', model_wrapper, bool_field, doc)
    assert extractor.extract_value() is False
    extractor = BooleanModelFieldExtractor(default_test_case, '1', model_wrapper, bool_field, doc)
    assert extractor.extract_value() is True
    extractor = BooleanModelFieldExtractor(default_test_case, 'true', model_wrapper, bool_field, doc)
    assert extractor.extract_value() is True
    extractor = BooleanModelFieldExtractor(default_test_case, None, model_wrapper, bool_field, doc)
    assert extractor.extract_value() is False


def test_model_field_extractor_extract_fk():
    """Check that the FK extractor tries to find a previous variable and handles everything as wanted."""
    fk_suite = PyTestTestSuite('foo')
    fk_test_case = fk_suite.create_and_add_test_case('bar')
    DjangoProject('django_sample_project.apps.config.settings')
    from django_sample_project.apps.order.models import Order
    from django.contrib.auth.models import User
    fk_field = ExistingModelFieldWrapper(Order._meta.get_field('owner'))
    doc = nlp('Gegeben sei ein Auftrag mit Alice als Besitzerin')
    statement = AssignmentStatement(
        expression=PyTestModelFactoryExpression(ExistingModelWrapper(User, None), [Kwarg('bar', 123)]),
        variable=Variable('alice', 'User'),
    )
    fk_test_case.add_statement(statement)
    # there should be a reference to the user in the statement above, so it should be returned
    extractor = ForeignKeyModelFieldExtractor(fk_test_case, doc[7], model_wrapper, fk_field, doc)
    assert extractor.extract_value() == statement.variable

    # if the variables don't match, there should be a warning
    extractor = ForeignKeyModelFieldExtractor(fk_test_case, 'asdasd', model_wrapper, fk_field, doc)
    assert isinstance(extractor.extract_value(), GenerationWarning)
    doc = nlp('Gegeben sei ein Auftrag mit Bob als Besitzer')   # <-- bob was not defined in a previous statement
    extractor = ForeignKeyModelFieldExtractor(fk_test_case, doc[7], model_wrapper, fk_field, doc)
    assert isinstance(extractor.extract_value(), GenerationWarning)


def test_model_field_extractor_extract_m2m():
    """M2M should always return None."""
    doc = nlp('Gegeben sei ein Todo, das aus dem anderen System kommt')
    extractor = M2MModelFieldExtractor(default_test_case, doc[9], model_wrapper, field, doc)
    assert extractor.extract_value() is None


def test_model_field_extractor_on_handled():
    """Check that the m2m extractor adds more statements to the original one."""
    m2m_suite = PyTestTestSuite('foo')
    m2m_test_case = m2m_suite.create_and_add_test_case('bar')
    DjangoProject('django_sample_project.apps.config.settings')
    m2m_source = Nlp.for_language(Languages.DE)('Die Todos 1 und 2 zugewiesen.')
    from django_sample_project.apps.order.models import Order, ToDo

    # create statements that indicate previous objects (to-dos) and add them to the test_case
    test_case_statement_1 = AssignmentStatement(
        expression=PyTestModelFactoryExpression(ExistingModelWrapper(ToDo, None), [Kwarg('bar', 123)]),
        variable=Variable('1', 'ToDo'),
    )
    test_case_statement_2 = AssignmentStatement(
        expression=PyTestModelFactoryExpression(ExistingModelWrapper(ToDo, None), [Kwarg('bar', 123)]),
        variable=Variable('2', 'ToDo'),
    )
    m2m_test_case.add_statement(test_case_statement_1)
    m2m_test_case.add_statement(test_case_statement_2)

    # create the statement for the factory of this object
    statement = AssignmentStatement(
        expression=PyTestModelFactoryExpression(ExistingModelWrapper(Order, None), [Kwarg('bar', 123)]),
        variable=Variable('order', 'Order'),
    )
    extractor = M2MModelFieldExtractor(
        m2m_test_case, m2m_source[1], model_wrapper, ExistingModelFieldWrapper(Order._meta.get_field('to_dos')), m2m_source)
    statements = [statement]
    assert len(statements) == 1

    # since we are searching for the todos 1 and 2, the two objects that were created earlier should be found
    # and added as statements
    extractor.on_handled_by_converter(statements)
    assert len(statements) == 3
    assert isinstance(statements[1].expression, ModelM2MAddExpression)
    assert isinstance(statements[2].expression, ModelM2MAddExpression)
