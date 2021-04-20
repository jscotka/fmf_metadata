import pytest
from fmf_metadata.base import FMF

# current solution based on https://github.com/pytest-dev/pytest/discussions/8554


class ItemsCollector:
    def pytest_collection_modifyitems(self, items):
        self.items = items[:]


def collect(opts):
    plugin_col = ItemsCollector()
    pytest.main(
        ["--collect-only", "-pno:terminal", "-m", ""] + opts, plugins=[plugin_col]
    )
    for item in plugin_col.items:
        func = item.function
        for marker in item.iter_markers():
            key = marker.name
            args = marker.args
            kwargs = marker.kwargs

            if key == "skip":
                FMF.enabled(False)(func)
            elif key == "skipif":
                # add skipif as tag as well (possible to use adjust, but conditions are python code)
                arg_string = "SKIP "
                if args:
                    arg_string += " ".join(map(str, args))
                if "reason" in kwargs:
                    arg_string += " " + kwargs["reason"]
                FMF.tag(arg_string)(func)
            elif key == "parametrize":
                # do nothing, parameters are already part of test name
                pass
            else:
                # generic mark store as tag
                FMF.tag(key)(func)
    return plugin_col.items
