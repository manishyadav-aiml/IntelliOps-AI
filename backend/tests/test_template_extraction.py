import pytest

from app.parsers.drain_parser import RegexTemplateExtractor, create_extractor

MESSAGES = [
    "User 102 connected to server 192.168.1.1",
    "User 204 connected to server 192.168.1.2",
    "User 305 connected to server 192.168.1.3",
]


def test_regex_extractor_groups_repeated_templates() -> None:
    extractor = RegexTemplateExtractor()
    results = [extractor.extract(m) for m in MESSAGES]
    assert {r.template_text for r in results} == {"User <*> connected to server <*>"}
    assert len({r.template_hash for r in results}) == 1
    assert [r.parameters for r in results][1] == ["204", "192.168.1.2"]


def test_different_messages_get_different_templates() -> None:
    extractor = RegexTemplateExtractor()
    a = extractor.extract("Database connection timeout after 30 seconds")
    b = extractor.extract("Disk usage at 91 percent")
    assert a.template_hash != b.template_hash


def test_empty_message_does_not_crash() -> None:
    result = RegexTemplateExtractor().extract("")
    assert result.template_text == "<empty>"


def test_factory_returns_a_working_extractor_even_without_drain3() -> None:
    extractor = create_extractor("drain")
    assert extractor.name in {"drain3", "regex-fallback"}
    for m in MESSAGES:
        extractor.learn(m)
    templates = {extractor.extract(m).template_text for m in MESSAGES}
    assert templates == {"User <*> connected to server <*>"}


def test_drain3_integration_when_installed() -> None:
    pytest.importorskip("drain3")
    extractor = create_extractor("drain")
    assert extractor.name == "drain3"
    for m in MESSAGES * 2:
        extractor.learn(m)
    results = [extractor.extract(m) for m in MESSAGES]
    assert len({r.template_text for r in results}) == 1
    assert "<*>" in results[0].template_text
    assert extractor.errors == 0
