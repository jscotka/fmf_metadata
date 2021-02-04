import argparse
import yaml
import sys
from fmf_metadata.base import (
    show,
    yaml_fmf_output,
    read_config,
)
from fmf_metadata.constants import MAIN_FMF, CONFIG_FMF_FILE

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
        help="root path to test",
    )
    parser.add_argument(
        "--config",
        dest="config",
        action="store",
        help="Config file for fmf formatter",
    )
    parser.add_argument("tests", nargs="*")
    return parser


def run():
    opts = arg_parser().parse_args()
    if not opts.fmf:
        show(path=opts.fmf_path, testfile_globs=opts.tests)
    else:
        config = dict()
        if opts.config:
            config = read_config(opts.config)
        fmf_file = config.get(CONFIG_FMF_FILE, MAIN_FMF)
        data = yaml_fmf_output(
            fmf_file=opts.fmf_file,
            path=opts.fmf_path,
            testfile_globs=opts.tests,
            config=config,
        )
        if opts.fmf_update:
            print(f"Update file: {fmf_file}")
            with open(fmf_file, "w") as fd:
                yaml.safe_dump(data, fd)
        else:
            yaml.safe_dump(data, sys.stdout)


if __name__ == "__main__":
    run()
