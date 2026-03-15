"""GDPR-06 consent stubs — Wave 0 (xfail until implemented)."""
import pytest


@pytest.mark.xfail(strict=False, reason="Wave 0 stub — implementation pending")
def test_consent_skips_when_sentinel_exists(brain_root):
    from engine.init_brain import prompt_consent, write_consent_sentinel

    write_consent_sentinel(brain_root)
    result = prompt_consent(brain_root)
    assert result is True


@pytest.mark.xfail(strict=False, reason="Wave 0 stub — implementation pending")
def test_consent_yes_flag_writes_sentinel(brain_root):
    from engine.init_brain import prompt_consent, check_consent

    result = prompt_consent(brain_root, yes=True)
    assert result is True
    assert check_consent(brain_root) is True


@pytest.mark.xfail(strict=False, reason="Wave 0 stub — implementation pending")
def test_consent_interactive_yes(brain_root, monkeypatch):
    from engine.init_brain import prompt_consent, check_consent

    monkeypatch.setattr("builtins.input", lambda _: "yes")
    result = prompt_consent(brain_root)
    assert result is True
    assert check_consent(brain_root) is True


@pytest.mark.xfail(strict=False, reason="Wave 0 stub — implementation pending")
def test_consent_interactive_no(brain_root, monkeypatch):
    from engine.init_brain import prompt_consent

    monkeypatch.setattr("builtins.input", lambda _: "no")
    result = prompt_consent(brain_root)
    assert result is False


@pytest.mark.xfail(strict=False, reason="Wave 0 stub — implementation pending")
def test_consent_eoferror_returns_false(brain_root, monkeypatch):
    from engine.init_brain import prompt_consent

    def raise_eof(_):
        raise EOFError

    monkeypatch.setattr("builtins.input", raise_eof)
    result = prompt_consent(brain_root)
    assert result is False
