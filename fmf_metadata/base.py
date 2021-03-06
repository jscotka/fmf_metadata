from typing import List
import io
import inspect
import unittest
import yaml
import importlib
import os
import glob
import sys
import ast
import fmf
import shlex
import re
from functools import lru_cache

from fmf_metadata.constants import (
    FMF_POSTFIX,
    FMF_ATTRIBUTES,
    FMF_ATTR_PREFIX,
    MAIN_FMF,
    TEST_METHOD_PREFIX,
    CONFIG_FMF_FILE,
    CONFIG_TESTGLOBS,
    CONFIG_TEST_PATH,
    CONFIG_POSTPROCESSING_TEST,
    CONFIG_ADDITIONAL_KEY,
    DESCRIPTION_KEY,
    SUMMARY_KEY,
    TEST_PATH,
    TESTFILE_GLOBS,
    CONFIG_MERGE_PLUS,
    CONFIG_MERGE_MINUS,
    ENVIRONMENT_KEY,
)


_ = shlex
# Handle both older and newer yaml loader
# https://msg.pyyaml.org/load
try:
    from yaml import FullLoader as YamlLoader
except ImportError:  # pragma: no cover
    from yaml import SafeLoader as YamlLoader


# Load all strings from YAML files as unicode
# https://stackoverflow.com/questions/2890146/
def construct_yaml_str(self, node):
    return self.construct_scalar(node)


YamlLoader.add_constructor("tag:yaml.org,2002:str", construct_yaml_str)


def debug_print(*args, **kwargs):
    kwargs["file"] = sys.stderr
    print(*args, **kwargs)


class _Test:
    def __init__(self, test):
        self.test = test
        if hasattr(test, "_testMethodName"):
            self.name = test._testMethodName
            self.method = getattr(test.__class__, test._testMethodName)
        else:
            self.name = test.function.__name__
            self.method = test.function


class _TestCls:
    def __init__(self, test_class, filename):
        self.file = filename
        self.cls = test_class
        self.name = test_class.__name__ if test_class is not None else None
        self.tests: List[_Test] = []


def filepath_tests(filename) -> List[_TestCls]:
    test_loader = unittest.TestLoader()
    output: List[_TestCls] = []
    loader = importlib.machinery.SourceFileLoader("non_important", filename)
    module = importlib.util.module_from_spec(
        importlib.util.spec_from_loader(loader.name, loader)
    )
    loader.exec_module(module)
    for test_suite in test_loader.loadTestsFromModule(module):
        for test in test_suite:
            cls = _TestCls(test.__class__, filename)
            if cls.name in [x for x in output if x.name == cls.name]:
                cls = [x for x in output if x.name == cls.name][0]
            else:
                output.append(cls)
            cls.tests.append(_Test(test))
    return output


def get_test_files(path, testfile_globs):
    output = list()
    for testfile_glob in testfile_globs:
        output += glob.glob(os.path.join(path, testfile_glob))
    if not output:
        raise FMFError(
            "There are no test in path {} via {}".format(path, testfile_globs)
        )
    return output


class Error(Exception):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return self.msg


class FMFError(Error):
    pass


def is_test_function(member):
    return inspect.isfunction(member) and member.__name__.startswith(TEST_METHOD_PREFIX)


def __set_method_attribute(item, attribute, value, post_mark, base_type=None):
    if post_mark not in FMF_POSTFIX:
        raise FMFError("as postfix you can use + or - or let it empty (FMF merging)")
    attr_postfixed = attribute + post_mark
    for postfix in set(FMF_POSTFIX) - {post_mark}:
        if hasattr(item, attribute + postfix):
            raise FMFError(
                "you are mixing various post_marks for {} ({} already exists)".format(
                    item, attribute + postfix
                )
            )
    if base_type is None:
        if isinstance(value, list) or isinstance(value, tuple):
            base_type = (list,)
        elif isinstance(value, dict):
            base_type = dict
            value = [value]
        else:
            value = [value]

    if isinstance(base_type, tuple) and base_type[0] in [tuple, list]:
        if not hasattr(item, attr_postfixed):
            setattr(item, attr_postfixed, list())
        # check expected object types for FMF attributes
        for value_item in value:
            if len(base_type) > 1 and not isinstance(value_item, tuple(base_type[1:])):
                raise FMFError(
                    "type {} (value:{}) is not allowed, please use: {} ".format(
                        type(value_item), value_item, base_type[1:]
                    )
                )
        getattr(item, attr_postfixed).extend(list(value))
        return

    # use just first value in case you don't use list of tuple
    if len(value) > 1:
        raise FMFError(
            "It is not permitted for {} (type:{}) put multiple values ({})".format(
                attribute, base_type, value
            )
        )
    first_value = value[0]
    if base_type and not isinstance(first_value, base_type):
        raise FMFError(
            "type {} (value:{}) is not allowed, please use: {} ".format(
                type(first_value), first_value, base_type
            )
        )
    if base_type in [dict]:
        if not hasattr(item, attr_postfixed):
            setattr(item, attr_postfixed, dict())
        first_value.update(getattr(item, attr_postfixed))
    if hasattr(item, attr_postfixed) and base_type not in [dict]:
        # if it is already defined (not list types or dict) exit
        # class decorators are applied right after, does not make sense to rewrite more specific
        # dict updating is reversed
        return
    setattr(item, attr_postfixed, first_value)


def set_obj_attribute(
    testEntity,
    attribute,
    value,
    raise_text=None,
    base_class=unittest.TestCase,
    base_type=None,
    post_mark="",
):
    if inspect.isclass(testEntity) and issubclass(testEntity, base_class):
        for test_function in inspect.getmembers(testEntity, is_test_function):
            __set_method_attribute(
                test_function[1],
                attribute,
                value,
                post_mark=post_mark,
                base_type=base_type,
            )
    elif is_test_function(testEntity):
        __set_method_attribute(
            testEntity, attribute, value, base_type=base_type, post_mark=post_mark
        )
    elif raise_text:
        raise FMFError(raise_text)
    return testEntity


def generic_metadata_setter(
    attribute,
    value,
    raise_text=None,
    base_class=unittest.TestCase,
    base_type=None,
    post_mark="",
):
    def inner(testEntity):
        return set_obj_attribute(
            testEntity,
            attribute,
            value,
            raise_text,
            base_class,
            base_type=base_type,
            post_mark=post_mark,
        )

    return inner


def fmf_prefixed_name(name):
    return FMF_ATTR_PREFIX + name


class __FMFMeta(type):
    @staticmethod
    def _set_fn(name, base_type=None):
        if name not in FMF_ATTRIBUTES:
            raise FMFError(
                "fmf decorator {} not found in {}".format(name, FMF_ATTRIBUTES.keys())
            )

        def inner(*args, post_mark=""):
            return generic_metadata_setter(
                fmf_prefixed_name(name),
                args,
                base_type=base_type or FMF_ATTRIBUTES[name],
                post_mark=post_mark,
            )

        return inner

    def __getattr__(cls, name):
        return cls._set_fn(name)


class FMF(metaclass=__FMFMeta):
    """
    This class implements class decorators for TMT semantics via dynamic class methods
    see https://tmt.readthedocs.io/en/latest/spec/tests.html
    """

    @classmethod
    def tag(cls, *args, post_mark=""):
        """
        generic purpose test tags to be used (e.g. "slow", "fast", "security")
        https://tmt.readthedocs.io/en/latest/spec/tests.html#tag
        """
        return cls._set_fn("tag", base_type=FMF_ATTRIBUTES["tag"])(
            *args, post_mark=post_mark
        )

    @classmethod
    def link(cls, *args, post_mark=""):
        """
        generic url links (default is verify) but could contain more see TMT doc
        https://tmt.readthedocs.io/en/latest/spec/core.html#link
        """
        return cls._set_fn("link", base_type=FMF_ATTRIBUTES["link"])(
            *args, post_mark=post_mark
        )

    @classmethod
    def bug(cls, *args, post_mark=""):
        """
        link to relevant bugs what this test verifies.
        It can be link to issue tracker or bugzilla
        https://tmt.readthedocs.io/en/latest/spec/tests.html#link
        """
        return cls.link(*[{"verifies": arg} for arg in args], post_mark=post_mark)

    @classmethod
    def adjust(
        cls, when, because=None, continue_execution=True, post_mark="", **kwargs
    ):
        """
        adjust testcase execution, see TMT specification
        https://tmt.readthedocs.io/en/latest/spec/core.html#adjust

        if key value arguments are passed they are applied as update of the dictionary items
        else disable test execution as default option

        e.g.

        @adjust("distro ~< centos-6", "The test is not intended for less than centos-6")
        @adjust("component == bash", "modify component", component="shell")

        tricky example with passing merging variables as kwargs to code
        because python does not allow to do parameter as X+="something"
        use **dict syntax for parameter(s)

        @adjust("component == bash", "append env variable", **{"environment+": {"BASH":true}})
        """
        adjust_item = dict()
        adjust_item["when"] = when
        if because is not None:
            adjust_item["because"] = because
        if kwargs:
            adjust_item.update(kwargs)
        else:
            adjust_item["enabled"] = False
        if continue_execution is False:
            adjust_item["continue"] = False
        return cls._set_fn("adjust", base_type=FMF_ATTRIBUTES["adjust"])(
            adjust_item, post_mark=post_mark
        )

    @classmethod
    def environment(cls, post_mark="", **kwargs):
        """
        environment testcase execution, see TMT specification
        https://tmt.readthedocs.io/en/latest/spec/test.html#environment

        add environment keys
        example:
        @environment(PYTHONPATH=".", DATA_DIR="test_data")
        """
        return cls._set_fn(ENVIRONMENT_KEY, base_type=FMF_ATTRIBUTES[ENVIRONMENT_KEY])(
            kwargs, post_mark=post_mark
        )


def identifier(text):
    return "/" + text


def default_key(parent_dict, key, empty_obj):
    if key not in parent_dict:
        output = empty_obj
        parent_dict[key] = output
        return output
    return parent_dict[key]


def __update_dict_key(method, key, fmf_key, dictionary, override_postfix=""):
    """
    This function have to ensure that there is righ one of attribute type extension
    and removes all others
    """
    value = None
    current_postfix = ""
    # find if item is defined inside method
    for attribute in dir(method):
        stripped = attribute.rstrip("".join(FMF_POSTFIX))
        if key == stripped:
            value = getattr(method, attribute)
            strip_len = len(stripped)
            current_postfix = attribute[strip_len:]
    # delete all keys in dictionary started with fmf_key
    for item in dictionary.copy():
        stripped = item.rstrip("".join(FMF_POSTFIX))
        if stripped == fmf_key:
            dictionary.pop(item)
    out_key = (
        fmf_key + override_postfix if override_postfix else fmf_key + current_postfix
    )
    if value is not None:
        dictionary[out_key] = value


def __get_fmf_attr_name(method, attribute):
    for current_attr in [fmf_prefixed_name(attribute + x) for x in FMF_POSTFIX]:
        if hasattr(method, current_attr):
            return current_attr
    return fmf_prefixed_name(attribute)


def __find_fmf_root(path):
    root = os.path.abspath(path)
    FMF_ROOT_DIR = ".fmf"
    while True:
        if os.path.exists(os.path.join(root, FMF_ROOT_DIR)):
            return root
        if root == os.path.sep:
            raise FMFError(
                "Unable to find FMF tree root for '{0}'.".format(os.path.abspath(path))
            )
        root = os.path.dirname(root)


def test_data_dict(
    test_dict, config, filename, cls, test, merge_plus_list=None, merge_minus_list=None
):
    merge_plus_list = merge_plus_list or config.get(CONFIG_MERGE_PLUS, [])
    merge_minus_list = merge_minus_list or config.get(CONFIG_MERGE_MINUS, [])
    doc_str = (test.method.__doc__ or "").strip("\n")
    # set summary attribute if not given by decorator
    current_name = __get_fmf_attr_name(test.method, SUMMARY_KEY)
    if not hasattr(test.method, current_name):
        # try to use first line of docstring if given
        if doc_str:
            summary = doc_str.split("\n")[0].strip()
        else:
            summary = (
                (f"{os.path.basename(filename)} " if filename else "")
                + (f"{cls.name} " if cls.name else "")
                + test.name
            )
        setattr(test.method, current_name, summary)

    # set description attribute by docstring if not given by decorator
    current_name = __get_fmf_attr_name(test.method, DESCRIPTION_KEY)
    if not hasattr(test.method, current_name):
        # try to use first line of docstring if given
        if doc_str:
            description = doc_str
            setattr(test.method, current_name, description)
    # generic FMF attributes set by decorators
    for key in FMF_ATTRIBUTES:
        # Allow to override key storing with merging postfixes
        override_postfix = ""
        if key in merge_plus_list:
            override_postfix = "+"
        elif key in merge_minus_list:
            override_postfix = "-"
        __update_dict_key(
            test.method,
            fmf_prefixed_name(key),
            key,
            test_dict,
            override_postfix,
        )

    # special config items
    if CONFIG_ADDITIONAL_KEY in config:
        for key, fmf_key in config[CONFIG_ADDITIONAL_KEY].items():
            __update_dict_key(test.method, key, fmf_key, test_dict)
    if CONFIG_POSTPROCESSING_TEST in config:
        __post_processing(
            test_dict, config[CONFIG_POSTPROCESSING_TEST], cls, test, filename
        )
    return test_dict


def yaml_fmf_output(
    path=None,
    testfile_globs=None,
    fmf_file=None,
    config=None,
    merge_plus_list=None,
    merge_minus_list=None,
):
    config = config or dict()
    # set values in priority 1. input param, 2. from config file, 3. default value
    fmf_file = fmf_file or config.get(CONFIG_FMF_FILE, MAIN_FMF)
    testfile_globs = testfile_globs or config.get(CONFIG_TESTGLOBS, TESTFILE_GLOBS)
    path = os.path.realpath(path or config.get(CONFIG_TEST_PATH, TEST_PATH))

    debug_print("Use config:", config)
    debug_print("Input FMF file:", fmf_file)
    debug_print("Tests path:", path)
    debug_print("Test globs:", testfile_globs)
    fmf_dict = dict()
    if fmf_file and os.path.exists(fmf_file):
        with open(fmf_file) as fd:
            fmf_dict = yaml.load(fd, Loader=YamlLoader) or fmf_dict
    for filename in get_test_files(path, testfile_globs):
        filename_dict = default_key(
            fmf_dict, identifier(os.path.basename(filename)), {}
        )
        for cls in filepath_tests(filename):
            class_dict = default_key(filename_dict, identifier(cls.name), {})
            for test in cls.tests:
                test_dict = default_key(class_dict, identifier(test.name), {})
                test_data_dict(
                    test_dict=test_dict,
                    config=config,
                    filename=filename,
                    cls=cls,
                    test=test,
                    merge_plus_list=merge_plus_list,
                    merge_minus_list=merge_minus_list,
                )
    return fmf_dict


def multiline_eval(expr, context, type_ignores=None):
    """Evaluate several lines of input, returning the result of the last line
    https://stackoverflow.com/questions/12698028/why-is-pythons-eval-rejecting-this-multiline-string-and-how-can-i-fix-it
    """
    tree = ast.parse(expr)
    eval_expr = ast.Expression(tree.body[-1].value)
    exec_expr = ast.Module(tree.body[:-1], type_ignores=type_ignores or [])
    exec(compile(exec_expr, "file", "exec"), context)
    return eval(compile(eval_expr, "file", "eval"), context)


def __post_processing(input_dict, config_dict, cls, test, filename):
    if isinstance(config_dict, dict):
        for k, v in config_dict.items():
            if isinstance(v, dict):
                if k not in input_dict:
                    input_dict[k] = dict()
                __post_processing(input_dict[k], v, cls, test, filename)
            else:
                input_dict[k] = multiline_eval(v, dict(locals(), **globals()))


def read_config(config_file):
    if not os.path.exists(config_file):
        raise FMFError(f"configuration files does not exists {config_file}")
    debug_print(f"Read config file: {config_file}")
    with open(config_file) as fd:
        return yaml.safe_load(fd)


def dict_to_yaml(data, width=None, sort=False):
    """ Convert dictionary into yaml """
    output = io.StringIO()
    try:
        yaml.safe_dump(
            data,
            output,
            sort_keys=sort,
            encoding="utf-8",
            allow_unicode=True,
            width=width,
            indent=4,
            default_flow_style=False,
        )
    except TypeError:
        # FIXME: Temporary workaround for rhel-8 to disable key sorting
        # https://stackoverflow.com/questions/31605131/
        # https://github.com/psss/tmt/issues/207
        def representer(self, data):
            self.represent_mapping("tag:yaml.org,2002:map", data.items())

        yaml.add_representer(dict, representer, Dumper=yaml.SafeDumper)
        yaml.safe_dump(
            data,
            output,
            encoding="utf-8",
            allow_unicode=True,
            width=width,
            indent=4,
            default_flow_style=False,
        )
    return output.getvalue()


def get_node(fmf_root, relative):
    tree = fmf.Tree(fmf_root)
    return tree.find(relative)


class StoreUpdater:
    def __init__(self):
        self._internal_dict = dict()

    def __getitem__(self, node):
        return self._internal_dict[node.name]

    def __setitem__(self, node, value):
        self._internal_dict[node.name] = [node, value]

    def has_key(self, node):
        return node.name in self._internal_dict

    def __repr__(self):
        return repr(self._internal_dict)

    def __len__(self):
        return len(self._internal_dict)

    def __delitem__(self, node):
        del self._internal_dict[node.name]

    def clear(self):
        return self._internal_dict.clear()

    def copy(self):
        return self._internal_dict.copy()

    def keys(self):
        return self._internal_dict.keys()

    def values(self):
        return self._internal_dict.values()

    def items(self):
        return self._internal_dict.items()

    def __cmp__(self, dict_):
        return self._internal_dict.__cmp__(self._internal_dict, dict_)

    def __contains__(self, node):
        return node.name in self._internal_dict

    def __iter__(self):
        return iter(self._internal_dict)

    def merge(self, node, input_dict):
        merge_dict(input_dict, self[node][1])


def merge_dict(source, destination):
    """https://stackoverflow.com/questions/20656135/python-deep-merge-dictionary-data"""
    for key, value in source.items():
        if isinstance(value, dict):
            # get node or create one
            node = destination.setdefault(key, {})
            merge_dict(value, node)
        else:
            destination[key] = value

    return destination


def update_fmf_file(func, config, write_dict):
    for item in func.items if hasattr(func, "items") else [func]:
        node, out_dict = _update_fmf_file(item, config=config)
        if node in write_dict:
            write_dict.merge(node, out_dict)
        else:
            write_dict[node] = out_dict
    return write_dict


def str_normalise(text):
    return "".join(x if (x.isalnum() or x in ["_", "."]) else "_" for x in text)


def define_undefined(input_dict, keys, config, relative_test_path, cls, test):
    for item in keys:
        item_id = f"/{item}"
        default_key(input_dict, item_id, empty_obj={})
        input_dict = input_dict[item_id]
    test_data_dict(
        test_dict=input_dict,
        config=config,
        filename=relative_test_path,
        cls=cls,
        test=test,
    )


@lru_cache(maxsize=None)
def get_cached_tree(path_loc):
    return fmf.Tree(path_loc)


def _update_fmf_file(func, config=None):
    cfg_file = os.getenv("CONFIG")
    if cfg_file:
        config = read_config(cfg_file)
    elif config and not isinstance(config, dict):
        config = read_config(config)
    else:
        config = config or {}
    fmf_file_location = func.fspath
    keys = list()
    file_loc = fmf_file_location
    base_file_name = os.path.basename(fmf_file_location)
    if os.path.exists(file_loc):
        if not os.path.isdir(file_loc):
            file_loc = os.path.dirname(file_loc)
    tree = get_cached_tree(file_loc)
    relative_path = file_loc.removeprefix(os.path.abspath(tree.root))

    # get all keys what has to be in FMF metadata tree
    keys += relative_path.strip("/").split("/")
    keys.append(os.path.basename(fmf_file_location))
    if func.cls:
        cls = _TestCls(func.cls, base_file_name)
        keys.append(cls.name)
    else:
        cls = _TestCls(None, base_file_name)
    test = _Test(func)
    # normalise test name to pytest identifier
    test.name = re.search(
        f".*({os.path.basename(func.function.__name__)}.*)", func.name
    ).group(1)
    # TODO: removed str_normalise(...) will see what happen
    keys.append(test.name)
    current = tree
    split_num = len(keys)
    for num, item in enumerate(keys):
        try:
            current = current[f"/{item}"]
        except KeyError:
            split_num = num
            break
    relative_test_path = os.path.join(
        file_loc.removeprefix(os.path.realpath(os.path.dirname(current.sources[-1]))),
        os.path.basename(fmf_file_location),
    )
    undefined_keys = keys[split_num:]
    store_dict = {}
    define_undefined(store_dict, undefined_keys, config, relative_test_path, cls, test)
    return current, store_dict


def store_to_fmf_files(stored_items, update=False):
    for node_name, value in stored_items.items():
        if update:
            changed = False
            for k, v in value[1].items():
                if k not in value[0].data or value[0].data[k] != v:
                    changed = True
                    break
            if changed:
                with value[0] as data:
                    data.update(value[1])
                debug_print(f"Updating node: {node_name} ({value[0].sources[-1]})")
            else:
                debug_print(f"Node not changed: {node_name} ({value[0].sources[-1]})")
        else:
            debug_print(f"Node: {node_name}")
            for line in dict_to_yaml(value[1]).splitlines():
                debug_print(f"\t{line}")
