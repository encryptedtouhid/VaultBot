"""Tests for the security policy engine."""

from vaultbot.security.policy import ActionSeverity, SecurityPolicy


def test_immutable_defaults_cannot_be_overridden() -> None:
    # Try to disable auth — should be forced back to True
    policy = SecurityPolicy({"auth.require_allowlist": False})
    assert policy.get("auth.require_allowlist") is True


def test_immutable_defaults_set_when_missing() -> None:
    policy = SecurityPolicy({})
    assert policy.get("auth.require_allowlist") is True
    assert policy.get("plugins.require_signature") is True
    assert policy.get("audit.enabled") is True


def test_requires_approval_for_medium_and_above() -> None:
    policy = SecurityPolicy()
    assert policy.requires_approval(ActionSeverity.INFO) is False
    assert policy.requires_approval(ActionSeverity.LOW) is False
    assert policy.requires_approval(ActionSeverity.MEDIUM) is True
    assert policy.requires_approval(ActionSeverity.HIGH) is True
    assert policy.requires_approval(ActionSeverity.CRITICAL) is True


def test_requires_cooldown() -> None:
    policy = SecurityPolicy()
    assert policy.requires_cooldown(ActionSeverity.MEDIUM) is False
    assert policy.requires_cooldown(ActionSeverity.HIGH) is True
    assert policy.requires_cooldown(ActionSeverity.CRITICAL) is True


def test_requires_2fa() -> None:
    policy = SecurityPolicy()
    assert policy.requires_2fa(ActionSeverity.HIGH) is False
    assert policy.requires_2fa(ActionSeverity.CRITICAL) is True


def test_classify_destructive_action() -> None:
    assert SecurityPolicy.classify_action("delete_file") == ActionSeverity.HIGH
    assert SecurityPolicy.classify_action("remove_user") == ActionSeverity.HIGH
    assert SecurityPolicy.classify_action("drop_table") == ActionSeverity.HIGH


def test_classify_sensitive_action() -> None:
    assert SecurityPolicy.classify_action("send_email") == ActionSeverity.MEDIUM
    assert SecurityPolicy.classify_action("execute_script") == ActionSeverity.MEDIUM


def test_classify_read_only_action() -> None:
    assert SecurityPolicy.classify_action("get_weather") == ActionSeverity.INFO
    assert SecurityPolicy.classify_action("list_files") == ActionSeverity.INFO
    assert SecurityPolicy.classify_action("search_contacts") == ActionSeverity.INFO


def test_classify_unknown_defaults_to_medium() -> None:
    assert SecurityPolicy.classify_action("do_something") == ActionSeverity.MEDIUM
