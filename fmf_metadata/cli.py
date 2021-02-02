import argparse
import yaml
import sys
from fmf_metadata.base import (
    MAIN_FMF,
    tests_path,
    TESTFILE_GLOBS,
    show,
    yaml_fmf_output,
)

# disable references inside yaml files
setattr(yaml.SafeDumper, "ignore_aliases", lambda *args: True)


def arg_parser():
    parser = argparse.ArgumentParser(
        description="FMF formatter and wrapper for running tests under pytest"
    )
    parser.add_argument(
        "-f", "--fmf", dest="fmf", action="store_true", help="Output to fmf format"
    )
    parser.add_argument(
        "--file",
        dest="fmf_file",
        action="store",
        default=MAIN_FMF,
        help="Output to fmf format",
    )
    parser.add_argument(
        "-u",
        "--update",
        dest="fmf_update",
        action="store_true",
        help="Output to fmf format",
    )
    parser.add_argument(
        "--path",
        dest="fmf_path",
        action="store",
        default=tests_path,
        help="root path to test",
    )
    parser.add_argument("tests", nargs="*", default=TESTFILE_GLOBS)
    return parser


def run():
    opts = arg_parser().parse_args()
    if not opts.fmf:
        show(path=opts.fmf_path, testfile_globs=opts.tests)
    else:
        data = yaml_fmf_output(
            fmf_file=opts.fmf_file, path=opts.fmf_path, testfile_globs=opts.tests
        )
        if opts.fmf_update:
            with open(opts.fmf_file, "w") as fd:
                yaml.safe_dump(data, fd)
        else:
            yaml.safe_dump(data, sys.stdout)


if __name__ == "__main__":
    run()
