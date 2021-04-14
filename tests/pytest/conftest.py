import pytest
from fmf_metadata.base import update_fmf_file
from fmf_metadata import constants

CONF = {
    constants.CONFIG_POSTPROCESSING_TEST: {
        "test": "f'python3 -m pytest -v {filename}"
        + """{("::" + str(cls.name)) if cls.name else ""}::{test.name}'"""
    }
}


@pytest.fixture(scope="session", autouse=True)
def store_fmf_metadata(request):
    update_fmf_file(request.node, config=CONF)
