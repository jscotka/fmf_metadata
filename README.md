# Python decorators for FMF metadata

FMF decorators for your python tests, see examples:

```buildoutcfg
fmf_metadata --path tests test-basic
```

or

```buildoutcfg
fmf_metadata --config tests/metadata_config.yaml
```

usage:

```buildoutcfg
usage: fmf_metadata [-h] [--file FMF_FILE] [-u] [--path FMF_PATH] [--config CONFIG] [--merge-plus MERGE_PLUS] [--merge-minus MERGE_MINUS]
                    [tests ...]

FMF formatter and wrapper for running tests under pytest

positional arguments:
  tests

optional arguments:
  -h, --help            show this help message and exit
  --file FMF_FILE       Use this FMF file (input and output when option --update)
  -u, --update          Update the selected FMF file
  --path FMF_PATH       root path to test
  --config CONFIG       Config file for fmf formatter
  --merge-plus MERGE_PLUS
                        override post_mark for item elements (change to +)
  --merge-minus MERGE_MINUS
                        override post_mark for item elements (change to -)

```

## Config file

You can define some command line options here, or extend possibilies of `fmf_metadata`
cli formatter.

- `additional_keys` - transform additional method variables to FMF keys
- `test_postprocessing` - add any other value to FMF test node. It is executed as python code.
  You can use (class `cls` (`class _TestCls`), or test method `test` (`class _Test`))
- `test_glob` - Override default test file glob list (CLI `tests`)
- `test_path` - Use selected path for tests (CLI `--path`)
- `fmf_file` - Use this file for fmf metadata (CLI `--file`)
- `merge_plus` - Override mentioned decorators contain FMF merging `+` (CLI `--merge-plus`)
- `merge_minus` - Override mentioned decorators contain FMF merging `-` (CLI `--merge-minus`)

### Example

```buildoutcfg
additional_keys:
  _generic_a: "generic_A"
  _generic_b: "generic_B"

test_postprocessing:
  environment:
    TEST_STR: '"{}.{}.{}".format(os.path.basename(cls.file), cls.name, test.name)'
    FMF_ROOT_DIR: "__find_fmf_root(cls.file)"
  random: '"value"'
  deep:
    struct:
      test: "cls.file"
      deeper:
        neco: '"out"'

test_glob: ["check-ex*"]
test_path: "tests/"
fmf_file: "/tmp/out.fmf"

merge_plus: ["tag"]

```
