from _pytest import config
from _pytest.main import Session


def collect(opts):
    conf = config.get_config(opts, plugins=[])
    conf.parse(opts)
    conf._do_configure()
    sess = Session.from_config(config=conf)

    conf.hook.pytest_sessionstart(session=sess)
    conf.hook.pytest_collection(session=sess)
    conf.hook.pytest_collection_finish(session=sess)

    return sess.items
