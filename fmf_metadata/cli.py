import argparse
import yaml
from fmf_metadata.base import (
    yaml_fmf_output,
    read_config,
    debug_print,
    dict_to_yaml,
    get_test_files,
    update_fmf_file,
)
from fmf_metadata.constants import MAIN_FMF, CONFIG_FMF_FILE, PYTEST_DEFAULT_CONF
from fmf_metadata.pytest_collector import collect

# disable references inside yaml files
setattr(yaml.SafeDumper, "ignore_aliases", lambda *args: True)


def arg_parser():
    parser = argparse.ArgumentParser(
        description="FMF formatter and wrapper for running tests under pytest"
    )
    parser.add_argument(
        "--file",
        dest="fmf_file",
        action="store",
        help="Use this FMF file (input and output when option --update)",
    )
    parser.add_argument(
        "-u",
        "--update",
        dest="fmf_update",
        action="store_true",
        help="Update the selected FMF file",
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
    parser.add_argument(
        "--merge-plus",
        dest="merge_plus",
        action="append",
        help="override post_mark for item elements (change to +)",
    )
    parser.add_argument(
        "--merge-minus",
        dest="merge_minus",
        action="append",
        help="override post_mark for item elements (change to -)",
    )
    parser.add_argument(
        "--pytest",
        dest="pytest_mode",
        action="store_true",
        help="Use pytest test collector, instead of default unittest",
    )

    parser.add_argument("tests", nargs="*")
    return parser


def run():
    opts = arg_parser().parse_args()
    config = dict()
    if opts.config:
        config = read_config(opts.config)
    if not opts.pytest_mode:
        fmf_file = opts.fmf_file or config.get(CONFIG_FMF_FILE, MAIN_FMF)
        data = yaml_fmf_output(
            fmf_file=opts.fmf_file,
            path=opts.fmf_path,
            testfile_globs=opts.tests,
            config=config,
            merge_minus_list=opts.merge_minus,
            merge_plus_list=opts.merge_plus,
        )
        if opts.fmf_update:
            debug_print(f"Update FMF file: {fmf_file}")
            with open(fmf_file, "w") as fd:
                fd.write(dict_to_yaml(data))
        else:
            print(dict_to_yaml(data))
    else:
        pytest_params = list()
        for item in get_test_files(opts.fmf_path or ".", opts.tests):
            pytest_params.append(item)

        for item in collect(pytest_params):
            if opts.fmf_update:
                update_fmf_file(item, config=config or PYTEST_DEFAULT_CONF)
            else:
                print(item)


if __name__ == "__main__":
    run()
