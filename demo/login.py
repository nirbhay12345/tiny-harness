import hashlib

USERS = {"alice": hashlib.sha256(b"hunter2").hexdigest()}


def check_password(username, password):
    stored = USERS.get(username)
    if stored is None:
        return False
    return stored == hashlib.sha256(password).hexdigest()
