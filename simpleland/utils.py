import uuid

def gen_id() -> str:
    return str(uuid.uuid1())