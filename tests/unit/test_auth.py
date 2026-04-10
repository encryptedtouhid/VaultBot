"""Tests for the authentication and authorization module."""

from zenbot.security.auth import AuthManager, Role


def test_unauthorized_user_is_rejected() -> None:
    auth = AuthManager()
    assert auth.is_authorized("telegram", "12345") is False


def test_authorized_user_is_accepted() -> None:
    auth = AuthManager({"telegram:12345": Role.USER})
    assert auth.is_authorized("telegram", "12345") is True


def test_admin_check() -> None:
    auth = AuthManager({
        "telegram:admin1": Role.ADMIN,
        "telegram:user1": Role.USER,
    })
    assert auth.is_admin("telegram", "admin1") is True
    assert auth.is_admin("telegram", "user1") is False
    assert auth.is_admin("telegram", "unknown") is False


def test_add_and_remove_user() -> None:
    auth = AuthManager()
    assert auth.is_authorized("discord", "99") is False

    auth.add_user("discord", "99", Role.USER)
    assert auth.is_authorized("discord", "99") is True

    auth.remove_user("discord", "99")
    assert auth.is_authorized("discord", "99") is False


def test_get_role() -> None:
    auth = AuthManager({"telegram:100": Role.ADMIN})
    assert auth.get_role("telegram", "100") == Role.ADMIN
    assert auth.get_role("telegram", "999") is None


def test_list_users() -> None:
    auth = AuthManager({
        "telegram:1": Role.ADMIN,
        "discord:2": Role.USER,
    })
    users = auth.list_users()
    assert users == {"telegram:1": "admin", "discord:2": "user"}


def test_cross_platform_isolation() -> None:
    auth = AuthManager({"telegram:100": Role.USER})
    assert auth.is_authorized("telegram", "100") is True
    assert auth.is_authorized("discord", "100") is False
