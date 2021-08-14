"""
This test includes integration tests which means it will check if the whole application works together as expected.
"""
import os
import pytest

from gherkin.compiler import GherkinToPyTestCompiler
from nlp.tests.utils import MockTranslator


@pytest.mark.parametrize(
    'input_file_name, output_file_name', [
        ('0001', '0001'),
        ('0002', '0002'),
        ('0003', '0003'),
        ('0004', '0004'),
        ('0005', '0005'),
        ('0006', '0006'),
        ('0007', '0007'),
        ('0008', '0008'),
        ('0009', '0009'),
        ('0010', '0010'),
    ]
)
def test_input_output_files(input_file_name, output_file_name, mocker):
    """Check that the input results in the correct output"""
    mocker.patch('deep_translator.GoogleTranslator.translate', MockTranslator())

    this_file_path = os.path.abspath(__file__).split('/')
    folder_path = this_file_path[:len(this_file_path) - 1]
    folder_path_as_str = '/'.join(folder_path)

    input_directory = '{}/input/'.format(folder_path_as_str)
    output_directory = '{}/output/'.format(folder_path_as_str)
    file_name_input = '{}{}.{}'.format(input_directory, input_file_name, 'feature')
    file_name_output = '{}{}.{}'.format(output_directory, output_file_name, 'py')

    with open(file_name_output) as file:
        output_text = file.read()

    output_lines = output_text.splitlines()
    compiler = GherkinToPyTestCompiler()

    compiler.compile_file(file_name_input)
    output = compiler.export_as_text()

    for i, line in enumerate(output.splitlines()):
        assert line == output_lines[i]
