from vmail.classify import flags


def test_role_account():
    f = flags("support@dentalkart.com")
    assert f.role is True
    assert f.disposable is False
    assert f.free is False


def test_disposable():
    f = flags("alt.sw-5v3dwdf@yopmail.com")
    assert f.disposable is True


def test_free_provider():
    f = flags("patilshelke888@gmail.com")
    assert f.free is True
    assert f.role is False


def test_personal_corporate():
    f = flags("jane@theorganicriot.com")
    assert (f.role, f.disposable, f.free) == (False, False, False)
