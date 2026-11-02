from login import check_password


def test_right_password():
    assert check_password("alice", "hunter2")


def test_wrong_password():
    assert not check_password("alice", "letmein")


def test_unknown_user():
    assert not check_password("ghost", "hunter2")
