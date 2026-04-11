"""Tests for webhook server utilities."""

from vaultbot.platforms.webhook_server import parse_query_params


def test_parse_empty_query() -> None:
    assert parse_query_params("") == {}


def test_parse_single_param() -> None:
    result = parse_query_params("key=value")
    assert result == {"key": "value"}


def test_parse_multiple_params() -> None:
    result = parse_query_params("a=1&b=2&c=3")
    assert result == {"a": "1", "b": "2", "c": "3"}


def test_parse_param_with_equals_in_value() -> None:
    result = parse_query_params("token=abc=def")
    assert result == {"token": "abc=def"}
