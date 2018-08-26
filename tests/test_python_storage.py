from io import StringIO

from pytest import fixture

from leancrawler import LeanFile


@fixture
def mocked_run_lean(mocker):
    mocker.patch('leancrawler.python_storage.LeanRunner.run', return_value='')


@fixture
def mocked_parse_lean(mocker):
    mocker.patch.object(LeanFile, 'parse_lean_output',
                        return_value=None)


def test_detect_import(mocked_run_lean, mocked_parse_lean):
    lf = LeanFile.from_stream(StringIO(
        "import data.list analysis.topological_space\nimport group"), '')
    assert set(lf.imports) == set(['data.list', 'analysis.topological_space',
                                   'group'])
