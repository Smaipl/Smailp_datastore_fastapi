import logging


log = logging.getLogger("datastore")


def dbg(*args, **kwargs):
    log.debug(*args, **kwargs, stacklevel=2)


def inf(*args, **kwargs):
    log.info(*args, **kwargs, stacklevel=2)
