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


@pytest.mark.slow
def test_slow():
    assert True


@pytest.mark.skipif(True, reason="skipping")
def test_skipif():
    assert False


@pytest.mark.skip(reason="Unconditional skipping")
def test_skip():
    assert False
