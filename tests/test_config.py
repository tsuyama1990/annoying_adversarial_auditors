from ac_cdd.config import settings


def test_config_agents_loaded():
    """Test that agents configuration is loaded correctly from ac_cdd.toml"""
    assert settings.agents.architect is not None
    assert "ソフトウェアアーキテクト" in settings.agents.architect
    assert "Jules" in settings.agents.coder
    assert "<thought>" in settings.agents.coder
    assert "Gemini" in settings.agents.auditor


def test_tools_config():
    """Test that tools configuration is loaded"""
    assert settings.tools.jules_cmd == "jules"
    assert settings.tools.gemini_cmd == "gemini"


def test_strict_audit_rules():
    """Verify stricter rules imply specific prompts"""
    assert "契約(Contract)のみ" in settings.agents.tester
