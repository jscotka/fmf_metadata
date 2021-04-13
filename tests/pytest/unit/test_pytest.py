import pytest
from fmf_metadata import FMF
import unittest


@FMF.tag("PASS")
def test_pass():
    assert True


@FMF.tag("FAIL")
def test_fail():
    assert False


class A(unittest.TestCase):
    def test(self):
        pass


@FMF.tag("PAR", "X")
@pytest.mark.parametrize("test_input", ["a", "b", "c"])
def test_param(test_input):
    print(test_input)
