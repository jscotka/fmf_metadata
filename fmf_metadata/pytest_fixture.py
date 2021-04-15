import os
import pytest

from fmf_metadata.base import update_fmf_file
from fmf_metadata import constants

CONF = {
    constants.CONFIG_POSTPROCESSING_TEST: {
        "test": """import shlex
cls_str = ("::" + str(cls.name)) if cls.name else ""
escaped = shlex.quote(f"{filename}{cls_str}::{test.name}")
f"python3 -m pytest -v {escaped}" """
    }
}


@pytest.fixture(scope="session", autouse=True)
def store_fmf_metadata(request):
    """
    If you want to regenerate FMF data, please install fmf_metadata project
    https://github.com/jscotka/fmf_metadata/
    """
    if os.getenv(constants.ENV_REGENERATE_FMF):
        update_fmf_file(request.node, config=CONF)
