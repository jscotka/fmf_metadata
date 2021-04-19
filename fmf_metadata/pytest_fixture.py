import os
import pytest

from fmf_metadata.base import update_fmf_file, StoreUpdater, store_to_fmf_files
from fmf_metadata import constants


@pytest.fixture(scope="session", autouse=True)
def store_fmf_metadata(request):
    """
    If you want to regenerate FMF data, please install fmf_metadata project
    https://github.com/jscotka/fmf_metadata/
    """
    if os.getenv(constants.ENV_REGENERATE_FMF):
        out = StoreUpdater()
        update_fmf_file(
            request.node, config=constants.PYTEST_DEFAULT_CONF, write_dict=out
        )
        store_to_fmf_files(out, True)
