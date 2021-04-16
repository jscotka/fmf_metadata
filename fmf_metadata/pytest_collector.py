import pytest
from fmf_metadata.base import FMF

# current solution based on https://github.com/pytest-dev/pytest/discussions/8554


class ItemsCollector:
    def pytest_collection_modifyitems(self, items):
        self.items = items[:]


def collect(opts):
    plugin_col = ItemsCollector()
    pytest.main(["--collect-only", "-m", ""] + opts, plugins=[plugin_col])
    for item in plugin_col.items:
        func = item.function
        for marker in item.iter_markers():
            key = marker.name
            args = marker.args
            kwargs = marker.kwargs

            if key == "skip":
                FMF.enabled(False)(func)
            elif key == "skipif":
                FMF.description(f"skipif: (cond: {args}) -> {kwargs}")(func)
            elif key == "parametrize":
                # do nothing, parameters are already part of test name
                pass
            else:
                # generic mark store as tag
                FMF.tag(key)(func)
    return plugin_col.items
