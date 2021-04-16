import unittest
import subprocess
import shutil
import yaml
import tempfile
import os

PYTEST_PATH = os.path.join(os.path.realpath(os.path.dirname(__file__)), "pytest")


class PytestFMF(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.mktemp()
        shutil.copytree(PYTEST_PATH, self.tempdir)
        self.main_fmf = os.path.join(self.tempdir, "unit", "main.fmf")

    def tearDown(self):
        shutil.rmtree(self.tempdir)
        pass

    def test(self):
        with open(self.main_fmf) as fd:
            out = yaml.load(fd)
            self.assertEqual(out["base"], "a")
            self.assertEqual(len(out), 1)
        out = subprocess.check_output(
            f"REGENERATE_FMF=yes pytest-3 -v {self.tempdir} 2>&1 || true", shell=True
        )
        for line in out.splitlines():
            print(line)
        with open(self.main_fmf) as fd:
            out = yaml.load(fd)
            self.assertEqual(out["base"], "a")
            self.assertGreater(len(out), 1)
            self.assertIn("/test_pass", out["/test_pytest.py"])
            self.assertIn("/test", out["/test_pytest.py"]["/A"])
            self.assertEqual(
                out["/test_pytest.py"]["/A"]["/test"]["test"],
                "python3 -m pytest -m '' -v test_pytest.py::A::test",
            )
            self.assertEqual(
                out["/test_pytest.py"]["/test_param_a_"]["__generated"], True
            )
            self.assertEqual(
                out["/test_pytest.py"]["/test_param_a_"]["summary"],
                "test_pytest.py test_param[a]",
            )
