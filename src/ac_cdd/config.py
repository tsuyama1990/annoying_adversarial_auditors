import tomllib
from pathlib import Path

from pydantic import ConfigDict, Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _detect_package_dir() -> str:
    """
    Detects the main package directory under src/.
    Looks for the first directory containing __init__.py.
    """
    src_path = Path("src")
    if src_path.exists():
        for p in src_path.iterdir():
            if p.is_dir() and (p / "__init__.py").exists():
                return str(p)
    # Fallback to standard conventions or strict default
    return "src/ac_cdd"


def _read_prompt(filename: str, default: str) -> str:
    p = Path("src/ac_cdd/prompts") / filename
    if p.exists():
        return p.read_text(encoding="utf-8").strip()
    return default


class PathsConfig(BaseSettings):
    model_config = ConfigDict(extra="ignore")
    documents_dir: str = "dev_documents"

    # Dynamic package detection
    package_dir: str = Field(default_factory=_detect_package_dir)

    # Dependent defaults (handled in validator)
    contracts_dir: str = ""

    sessions_dir: str = ".jules/sessions"
    src: str = "src"
    tests: str = "tests"
    templates: str = "dev_documents/templates"

    # Test subdirectories
    property_tests: str = "tests/property"
    unit_tests: str = "tests/unit"
    e2e_tests: str = "tests/e2e"

    @model_validator(mode="after")
    def _set_dependent_paths(self) -> "PathsConfig":
        if not self.contracts_dir:
            self.contracts_dir = f"{self.package_dir}/contracts"
        return self


class ToolsConfig(BaseSettings):
    model_config = ConfigDict(extra="ignore")
    jules_cmd: str = "jules"
    gh_cmd: str = "gh"
    audit_cmd: str = "bandit"
    uv_cmd: str = "uv"
    mypy_cmd: str = "mypy"
    ruff_cmd: str = "ruff"
    gemini_cmd: str = "gemini"
    jules_base_url: str = "https://jules.googleapis.com/v1alpha"


class SandboxConfig(BaseSettings):
    """Configuration for E2B Sandbox execution"""

    model_config = ConfigDict(extra="ignore")
    cwd: str = "/home/user"
    dirs_to_sync: list[str] = ["src", "tests", "contracts", "dev_documents"]
    files_to_sync: list[str] = ["pyproject.toml", "uv.lock", ".auditignore"]

    # Commands to run in sandbox
    install_cmd: str = "pip install uv"
    test_cmd: list[str] = ["uv", "run", "pytest"]
    lint_check_cmd: list[str] = ["uv", "run", "ruff", "check", "--fix", "."]
    type_check_cmd: list[str] = ["uv", "run", "mypy", "src/"]
    security_check_cmd: list[str] = ["uv", "run", "bandit", "-r", "src/", "-ll"]


class AgentsConfig(BaseSettings):
    model_config = ConfigDict(extra="ignore")
    architect: str = Field(
        default_factory=lambda: _read_prompt("architect.md", "DEFAULT_ARCHITECT_PROMPT")
    )
    coder: str = Field(
        default_factory=lambda: _read_prompt("coder.md", "DEFAULT_CODER_PROMPT")
    )
    tester: str = Field(
        default_factory=lambda: _read_prompt("tester.md", "DEFAULT_TESTER_PROMPT")
    )
    auditor: str = Field(
        default_factory=lambda: _read_prompt("auditor.md", "DEFAULT_AUDITOR_PROMPT")
    )
    qa_analyst: str = Field(
        default_factory=lambda: _read_prompt("qa_analyst.md", "DEFAULT_QA_ANALYST_PROMPT")
    )


class PromptsConfig(BaseSettings):
    model_config = ConfigDict(extra="ignore")
    property_test_template: str = Field(
        default_factory=lambda: _read_prompt("property_test_template.md", "DEFAULT_TEST_PROMPT")
    )


class Settings(BaseSettings):
    MAX_RETRIES: int = 10
    DUMMY_CYCLE_ID: str = "00"

    paths: PathsConfig = PathsConfig()
    tools: ToolsConfig = ToolsConfig()
    sandbox: SandboxConfig = SandboxConfig()
    agents: AgentsConfig = AgentsConfig()
    prompts: PromptsConfig = PromptsConfig()

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @classmethod
    def load_from_toml(cls, toml_path: str = "ac_cdd.toml") -> "Settings":
        # Load from toml manually since pydantic-settings generic support
        # is often via extra dependencies or specific source classes.
        # Here we mix environment variables (default behavior) with TOML values.

        # Initialize with defaults/env vars
        settings = cls()

        path = Path(toml_path)
        if path.exists():
            with open(path, "rb") as f:
                data = tomllib.load(f)

            # Update nested models if keys exist in TOML
            if "paths" in data:
                settings.paths = PathsConfig(**data["paths"])
            if "tools" in data:
                settings.tools = ToolsConfig(**data["tools"])
            if "sandbox" in data:
                settings.sandbox = SandboxConfig(**data["sandbox"])
            # Note: agents and prompts are now loaded from files by default,
            # but we allow overriding from TOML if specified explicitly (though deprecated)
            if "agents" in data:
                settings.agents = AgentsConfig(**data["agents"])
            if "prompts" in data:
                settings.prompts = PromptsConfig(**data["prompts"])

        return settings


settings = Settings.load_from_toml()
