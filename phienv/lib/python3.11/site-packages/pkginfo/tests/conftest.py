import pathlib
import tempfile

import pytest

@pytest.fixture(scope="module")
def here():
    file_path = pathlib.Path(__file__)
    return file_path.parent

@pytest.fixture(scope="module")
def examples_dir(here):
    return here / "../../docs/examples"

_ARCHIVE_FILENAMES = [
    'mypackage-0.1.tar',
    'mypackage-0.1.tar.gz',
    'mypackage-0.1.tar.bz2',
    'mypackage-0.1.zip',
]
@pytest.fixture(scope="module", params=_ARCHIVE_FILENAMES)
def archive(examples_dir, request):
    yield examples_dir / request.param

@pytest.fixture(scope="module")
def test_egg(examples_dir):
    yield examples_dir / 'mypackage-0.1-py2.6.egg'

@pytest.fixture(scope="module")
def test_wheel(examples_dir):
    yield examples_dir / 'mypackage-0.1-cp26-none-linux_x86_64.whl'

@pytest.fixture()
def temp_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        return pathlib.Path(tmpdir)

