"""Tests for engine/classifier.py — PII classification (AI-02)."""
import pytest


def test_frontmatter_pii_wins():
    """classify('pii', anything) returns 'pii' regardless of body."""
    from engine.classifier import classify
    assert classify("pii", "") == "pii"
    assert classify("pii", "clean architecture notes") == "pii"


def test_frontmatter_private_wins():
    """classify('private', anything) returns 'private'."""
    from engine.classifier import classify
    assert classify("private", "") == "private"
    assert classify("private", "totally clean body") == "private"


def test_frontmatter_public_wins():
    """classify('public', anything) returns 'public' — even if body has PII keywords."""
    from engine.classifier import classify
    assert classify("public", "salary is 100k") == "public"


def test_keyword_scan_triggers_pii():
    """classify('', body_with_pii_keyword) returns 'pii'."""
    from engine.classifier import classify
    assert classify("", "salary is 100k") == "pii"
    assert classify("", "medical diagnosis required") == "pii"
    assert classify("", "my SSN is 123-45-6789") == "pii"


def test_clean_body_returns_public():
    """classify('', clean body) returns 'public'."""
    from engine.classifier import classify
    assert classify("", "architecture notes about microservices") == "public"
    assert classify("invalid_value", "clean body") == "public"
