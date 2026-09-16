"""
Tests for governance: privacy, secret vaulting, and compliance reporting.
"""

from skillgenie.config import Config
from skillgenie.governance.manager import GovernanceManager
from skillgenie.governance.privacy import PrivacyGovernor
from skillgenie.governance.vault import SecretVault


def _privacy(tmp_path):
    return PrivacyGovernor(Config(str(tmp_path / "config.json")))


def test_redacts_email(tmp_path):
    privacy = _privacy(tmp_path)

    redacted = privacy.redact("contact sachin@example.com now")

    assert "sachin@example.com" not in redacted
    assert "EMAIL_REDACTED" in redacted


def test_redacts_dictionary_recursively(tmp_path):
    privacy = _privacy(tmp_path)

    value = {
        "user": "alice@corp.io",
        "settings": {"phone": "+1 555 123 4567"},
    }

    redacted = privacy.redact(value)

    assert "alice@corp.io" not in str(redacted)
    assert redacted["settings"]["phone"] != value["settings"]["phone"]


def test_redacts_secret_keys(tmp_path):
    privacy = _privacy(tmp_path)

    redacted = privacy.redact({"api_key": "sk-live-123", "name": "ok"})

    assert redacted["api_key"] == "[REDACTED]"
    assert redacted["name"] == "ok"


def test_inspect_counts_pii(tmp_path):
    privacy = _privacy(tmp_path)

    counts = privacy.inspect("email me at a@b.com, call +44 20 1234 5678")

    assert counts.get("email", 0) >= 1
    assert counts.get("phone", 0) >= 1


def test_data_residency_rules(tmp_path):
    privacy = _privacy(tmp_path)

    assert privacy.allows_provider("self-hosted") is True
    assert privacy.allows_provider("local") is True
    assert privacy.allows_provider("global") is False


def test_vault_roundtrip_file_backend(tmp_path):
    vault = SecretVault(path=str(tmp_path / "secrets"))

    vault.set("openrouter", "sk-abc")

    assert vault.get("openrouter") == "sk-abc"
    assert "openrouter" in vault.list_names()

    vault.delete("openrouter")

    assert vault.get("openrouter") is None


def test_vault_encrypts_when_key_present(tmp_path, monkeypatch):
    monkeypatch.setenv("VAULT_KEY", "A" * 32)
    vault = SecretVault(
        path=str(tmp_path / "secrets"),
        vault_key_env="VAULT_KEY",
    )

    vault.set("api-key", "super-secret-value")

    stored_payload = (tmp_path / "secrets" / "vault.json").read_text(
        encoding="utf-8"
    )

    assert "super-secret-value" not in stored_payload
    assert vault.get("api-key") == "super-secret-value"


def test_governance_manager_report(tmp_path):
    manager = GovernanceManager(Config(str(tmp_path / "config.json")))

    report = manager.report()

    assert report["telemetry_enabled"] is True
    assert report["data_residency"] == "self-hosted"
    assert "vault_secrets" in report