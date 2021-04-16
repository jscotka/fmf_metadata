import pytest

# current solution based on https://github.com/pytest-dev/pytest/discussions/8554


class ItemsCollector:
    def pytest_collection_modifyitems(self, items):
        self.items = items[:]


def collect(opts):
    plugin_col = ItemsCollector()
    pytest.main(["--collect-only", "-m", "''"] + opts, plugins=[plugin_col])
    return plugin_col.items
