import uuid


def gen_id(prefix=None):
    return uuid.uuid1()
