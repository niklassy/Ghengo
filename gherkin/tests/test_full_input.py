import os
from os import listdir
from os.path import isfile, join

import pytest

from gherkin.compiler import GherkinToPyTestCompiler
from gherkin.exception import GherkinInvalid
from test_utils import assert_callable_raises

THIS_FILE_PATH = os.path.abspath(__file__).split('/')
THIS_FOLDER = THIS_FILE_PATH[:len(THIS_FILE_PATH) - 1]
FOLDER_STR_INVALID = '/'.join(THIS_FOLDER + ['invalid_feature_files'])
FOLDER_STR_VALID = '/'.join(THIS_FOLDER + ['valid_feature_files'])


def get_feature_paths_in_folder(folder_path):
    return ['{}/{}'.format(folder_path, f) for f in listdir(folder_path) if isfile(join(folder_path, f))]


FEATURE_PATHS_VALID = get_feature_paths_in_folder(FOLDER_STR_VALID)
FEATURE_PATHS_INVALID = get_feature_paths_in_folder(FOLDER_STR_INVALID)


@pytest.mark.parametrize(
    'invalid_feature_path', FEATURE_PATHS_INVALID
)
def test_invalid_files(invalid_feature_path):
    assert_callable_raises(
        GherkinToPyTestCompiler().compile_file,
        GherkinInvalid,
        args=[invalid_feature_path]
    )


@pytest.mark.parametrize(
    'valid_feature_path', FEATURE_PATHS_VALID
)
def test_valid_files(valid_feature_path):
    GherkinToPyTestCompiler().compile_file(valid_feature_path)
