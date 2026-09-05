from rt_connect_api.core.logging import _redact


def test_sensitive_keys_and_database_password_are_redacted() -> None:
    event = _redact(
        None,
        "test",
        {
            "authorization": "Bearer should-not-leak",
            "database_url": "postgresql://name:password@example.test/app",
            "message": "connection postgresql://name:password@example.test/app failed",
        },
    )

    assert event["authorization"] == "[REDACTED]"
    assert event["database_url"] == "[REDACTED]"
    assert "password" not in event["message"]
