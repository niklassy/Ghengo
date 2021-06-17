# TODO: FIX!!!
# from decimal import Decimal
#
# from django_meta.project import AbstractModelInterface, AbstractModelField, DjangoProject, ModelInterface
# from nlp.extractor import ModelFieldExtractor
# from nlp.generate.argument import Kwarg
# from nlp.generate.expression import ModelM2MAddExpression
# from nlp.generate.pytest import PyTestModelFactoryExpression
# from nlp.generate.pytest.suite import PyTestTestSuite
# from nlp.generate.statement import AssignmentStatement
# from nlp.generate.variable import Variable
# from nlp.setup import Nlp
#
# suite = PyTestTestSuite('bar')
# test_case = suite.create_and_add_test_case('foo')
# model_interface = AbstractModelInterface('Order')
# field = AbstractModelField('name')
# source = Nlp.for_language('de')('Sie hat 3 Äpfel.')
#
#
# def test_model_field_extractor_extract_number():
#     """Checks if the number is correctly extracted."""
#     extractor = ModelFieldExtractor(test_case, 'pre_value', None, model_interface, field)
#     assert extractor.extract_number_for_field() == 'pre_value'
#     extractor_2 = ModelFieldExtractor(test_case, 'pre_value', source[3], model_interface, field)
#     assert extractor_2.extract_number_for_field() == '3'
#
#
# def test_model_field_extractor_for_integer():
#     """Check if the value for an integer field is correctly extracted."""
#     extractor = ModelFieldExtractor(test_case, 'pre_value', source[3], model_interface, field)
#     assert extractor.get_value_for_integer_field() == 3
#
#
# def test_model_field_extractor_for_float():
#     """Check if the value for an float field is correctly extracted."""
#     extractor = ModelFieldExtractor(test_case, 'pre_value', source[3], model_interface, field)
#     assert extractor.get_value_for_float_field() == 3.0
#
#
# def test_model_field_extractor_for_decimal():
#     """Check if the value for an decimal field is correctly extracted."""
#     extractor = ModelFieldExtractor(test_case, 'pre_value', source[3], model_interface, field)
#     assert extractor.get_value_for_decimal_field() == Decimal(3)
#
#
# def test_model_field_extractor_for_boolean():
#     """Check if the value for an boolean field is correctly extracted."""
#     boolean_source_false = Nlp.for_language('de')('Er spielt nicht mit dem Auto.')
#     extractor = ModelFieldExtractor(test_case, 'pre_value', boolean_source_false[1], model_interface, field)
#     assert extractor.get_value_for_boolean_field() is False
#     boolean_source_true = Nlp.for_language('de')('Er spielt mit dem Auto.')
#     extractor = ModelFieldExtractor(test_case, 'pre_value', boolean_source_true[1], model_interface, field)
#     assert extractor.get_value_for_boolean_field() is True
#
#
# def test_model_field_extractor_default_value():
#     """Check if the default value is correctly accessed."""
#     extractor = ModelFieldExtractor(test_case, 'pre_value', source[3], model_interface, field)
#     assert extractor.get_default_value() == 'pre_value'
#     extractor = ModelFieldExtractor(test_case, '"pre_value"', source[3], model_interface, field)
#     assert extractor.get_default_value() == 'pre_value'
#     extractor = ModelFieldExtractor(test_case, '', None, model_interface, field)
#     assert extractor.get_default_value() == ''
#
#
# def test_model_field_extractor_for_fk():
#     """Check if extracting the value for a fk works as expected."""
#     fk_suite = PyTestTestSuite('foo')
#     fk_test_case = fk_suite.create_and_add_test_case('bar')
#     DjangoProject('django_sample_project.apps.config.settings')
#     from django_sample_project.apps.order.models import Order
#     from django.contrib.auth.models import User
#     statement = AssignmentStatement(
#         expression=PyTestModelFactoryExpression(ModelInterface(User, None), [Kwarg('bar', 123)]),
#         variable=Variable('user', 'User'),
#     )
#     fk_test_case.add_statement(statement)
#     # there should be a reference to the user in the statement above, so it should be returned
#     extractor = ModelFieldExtractor(fk_test_case, 'user', source[3], model_interface, Order._meta.get_field('owner'))
#     assert extractor.get_value_for_fk_field() == statement.variable
#
#     # if the variables don't match, just return a string
#     extractor = ModelFieldExtractor(fk_test_case, 'asdasd', source[3], model_interface, Order._meta.get_field('owner'))
#     assert extractor.get_value_for_fk_field() == 'asdasd'
#
#
# def test_model_field_extractor_statement_side_effects():
#     """Check if for m2m fields, more statements are created as a side effect."""
#     m2m_suite = PyTestTestSuite('foo')
#     m2m_test_case = m2m_suite.create_and_add_test_case('bar')
#     DjangoProject('django_sample_project.apps.config.settings')
#     m2m_source = Nlp.for_language('de')('Die Todos 1 und 2 zugewiesen.')
#     from django_sample_project.apps.order.models import Order, ToDo
#
#     # create statements that indicate previous objects (to-dos) and add them to the test_case
#     test_case_statement_1 = AssignmentStatement(
#         expression=PyTestModelFactoryExpression(ModelInterface(ToDo, None), [Kwarg('bar', 123)]),
#         variable=Variable('1', 'ToDo'),
#     )
#     test_case_statement_2 = AssignmentStatement(
#         expression=PyTestModelFactoryExpression(ModelInterface(ToDo, None), [Kwarg('bar', 123)]),
#         variable=Variable('2', 'ToDo'),
#     )
#     m2m_test_case.add_statement(test_case_statement_1)
#     m2m_test_case.add_statement(test_case_statement_2)
#
#     # create the statement for the statement that was created previously
#     statement = AssignmentStatement(
#         expression=PyTestModelFactoryExpression(ModelInterface(Order, None), [Kwarg('bar', 123)]),
#         variable=Variable('order', 'Order'),
#     )
#     extractor = ModelFieldExtractor(
#         m2m_test_case, m2m_source[2], m2m_source[2], model_interface, Order._meta.get_field('to_dos'))
#     statements = [statement]
#     assert len(statements) == 1
#
#     # since we are searching for the todos 1 and 2, the two objects that were created earlier should be found
#     # and added as statements
#     extractor.append_side_effect_statements(statements)
#     assert len(statements) == 3
#     assert isinstance(statements[1].expression, ModelM2MAddExpression)
#     assert isinstance(statements[2].expression, ModelM2MAddExpression)
