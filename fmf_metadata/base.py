import inspect
import unittest
import yaml
import importlib
import os
import glob

TEST_PATH = os.path.realpath(os.getenv("TEST_PATH", "."))

TESTFILE_GLOBS = ["test-*"]
MAIN_FMF = "main.fmf"
SUMMARY_KEY = "summary"
DESCRIPTION_KEY = "description"
ENVIRONMENT_KEY = "environment"
TEST_METHOD_PREFIX = "test"
FMF_ATTRIBUTES = {
    SUMMARY_KEY: str,
    DESCRIPTION_KEY: str,
    "order": int,
    "adjust": (
        list,
        dict,
    ),
    "tag": (
        list,
        str,
    ),
    "link": (list, str, dict),
    "duration": str,
    "tier": str,
    "component": (
        list,
        str,
    ),
    "require": (
        list,
        str,
    ),
    "test": (str,),
    "framework": (str,),
    ENVIRONMENT_KEY: (
        dict,
        str,
    ),
    "path": (str,),
}
FMF_ATTR_PREFIX = "_fmf__"
FMF_POSTFIX = ("+", "-", "")

CONFIG_ADDITIONAL_KEY = "additional_keys"
CONFIG_POSTPROCESSING_TEST = "test_postprocessing"
CONFIG_TESTGLOBS = "test_glob"
CONFIG_TEST_PATH = "test_path"
CONFIG_FMF_FILE = "fmf_file"


def filepath_tests(filename):
    test_loader = unittest.TestLoader()
    output = dict()
    loader = importlib.machinery.SourceFileLoader("non_important", filename)
    module = importlib.util.module_from_spec(
        importlib.util.spec_from_loader(loader.name, loader)
    )
    loader.exec_module(module)
    for test_suite in test_loader.loadTestsFromModule(module):
        for test in test_suite:
            cls_name = test.__class__.__name__
            test_method_name = test._testMethodName
            test_method = getattr(test.__class__, test._testMethodName)
            if cls_name not in output:
                output[cls_name] = {"class": test.__class__, "tests": {}}
            output[cls_name]["tests"][test_method_name] = {
                "unittest": test,
                "method": test_method,
            }
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
        https://tmt.readthedocs.io/en/latest/spec/tests.html#link
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
        return cls.link(*[{"verify": arg} for arg in args], post_mark=post_mark)


def identifier(text):
    return "/" + text


def default_key(parent_dict, key, empty_obj):
    if key not in parent_dict:
        output = empty_obj
        parent_dict[key] = output
        return output
    return parent_dict[key]


def __update_dict_key(method, key, fmf_key, dictionary):
    """
    This function have to ensure that there is righ one of attribute type extension
    and removes all others
    """
    for postfix in FMF_POSTFIX:
        curr_fmf_key = fmf_key + postfix
        value = getattr(method, key + postfix, None)
        if curr_fmf_key in dictionary:
            dictionary.pop(curr_fmf_key)
        if value is not None:
            dictionary[curr_fmf_key] = value


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


def yaml_fmf_output(path=None, testfile_globs=None, fmf_file=None, config_file=None):
    config = dict()
    if config_file:
        if not os.path.exists(config_file):
            raise FMFError(f"configuration files does not exists {config_file}")
        print(f"using config: {config_file}")
        with open(config_file) as fd:
            config = yaml.safe_load(fd)
    # set values in priority 1. input param, 2. from config file, 3. default value
    fmf_file = fmf_file or config.get(CONFIG_FMF_FILE, MAIN_FMF)
    testfile_globs = testfile_globs or config.get(CONFIG_TESTGLOBS, TESTFILE_GLOBS)
    path = os.path.realpath(path or config.get(CONFIG_TEST_PATH, TEST_PATH))
    print(config)
    print(fmf_file, testfile_globs, path)
    fmf_dict = dict()
    if fmf_file and os.path.exists(fmf_file):
        with open(fmf_file) as fd:
            fmf_dict = yaml.safe_load(fd)
    for filename in get_test_files(path, testfile_globs):
        filename_dict = default_key(
            fmf_dict, identifier(os.path.basename(filename)), {}
        )
        for class_name, items in filepath_tests(filename).items():
            class_dict = default_key(filename_dict, identifier(class_name), {})
            for test_name, items2 in items["tests"].items():
                test_dict = default_key(class_dict, identifier(test_name), {})
                doc_str = (items2["method"].__doc__ or "").strip("\n")
                # set summary attribute if not given by decorator
                current_name = __get_fmf_attr_name(items2["method"], SUMMARY_KEY)
                if not hasattr(items2["method"], current_name):
                    # try to use first line of docstring if given
                    if doc_str:
                        summary = doc_str.split("\n")[0].strip()
                    else:
                        summary = "{} {} {}".format(
                            os.path.basename(filename), class_name, test_name
                        )
                    setattr(items2["method"], current_name, summary)

                # set description attribute by docstring if not given by decorator
                current_name = __get_fmf_attr_name(items2["method"], DESCRIPTION_KEY)
                if not hasattr(items2["method"], current_name):
                    # try to use first line of docstring if given
                    if doc_str:
                        description = doc_str
                        setattr(items2["method"], current_name, description)
                # generic FMF attributes set by decorators
                for key in FMF_ATTRIBUTES:
                    __update_dict_key(
                        items2["method"], fmf_prefixed_name(key), key, test_dict
                    )
                # special config items
                if CONFIG_ADDITIONAL_KEY in config:
                    for key, fmf_key in config[CONFIG_ADDITIONAL_KEY].items():
                        __update_dict_key(items2["method"], key, fmf_key, test_dict)
                if CONFIG_POSTPROCESSING_TEST in config:
                    print("postprocessing")
                    __post_processing(
                        test_dict,
                        config[CONFIG_POSTPROCESSING_TEST],
                        filename,
                        class_name,
                        test_name,
                    )
    return fmf_dict


def __post_processing(input_dict, config_dict, filename, class_name, test_name):
    if isinstance(config_dict, dict):
        for k, v in config_dict.items():
            if isinstance(v, dict):
                if k not in input_dict:
                    input_dict[k] = dict()
                __post_processing(input_dict[k], v, filename, class_name, test_name)
            else:
                input_dict[k] = eval(v)


def show(path, testfile_globs, indent="  "):
    for filename in get_test_files(path, testfile_globs):
        print(os.path.basename(filename))
        for class_name, items in filepath_tests(filename).items():
            print(indent, class_name)
            for test_name, items2 in items["tests"].items():
                print(indent * 2, test_name)
