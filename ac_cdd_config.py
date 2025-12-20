from pathlib import Path

from pydantic import Field, model_validator
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
    return "src/ac_cdd_core"


def _read_prompt(filename: str, default: str) -> str:
    p = Path("src/ac_cdd_core/prompts") / filename
    if p.exists():
        return p.read_text(encoding="utf-8").strip()
    return default


class PathsConfig(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")
    documents_dir: str = "dev_documents"
    package_dir: str = Field(default_factory=_detect_package_dir)
    contracts_dir: str = ""
    sessions_dir: str = ".jules/sessions"
    src: str = "src"
    tests: str = "tests"
    templates: str = "dev_documents/templates"
    property_tests: str = "tests/property"
    unit_tests: str = "tests/unit"
    e2e_tests: str = "tests/e2e"
    # New: Prompts directory path
    prompts_dir: str = "src/ac_cdd_core/prompts"

    @model_validator(mode="after")
    def _set_dependent_paths(self) -> "PathsConfig":
        if not self.contracts_dir:
            self.contracts_dir = f"{self.package_dir}/contracts"
        return self

class JulesConfig(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")
    # Point to the mock script by default for this environment
    executable: str = str(Path("tests/mock_jules.py").absolute())
    timeout_seconds: int = 600
    polling_interval_seconds: int = 5


class ToolsConfig(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")
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

    model_config = SettingsConfigDict(extra="ignore")
    template: str | None = None  # None uses default (base)
    timeout: int = 300  # Default timeout in seconds
    cwd: str = "/home/user"
    dirs_to_sync: list[str] = ["src", "tests", "contracts", "dev_documents"]
    files_to_sync: list[str] = ["pyproject.toml", "uv.lock", ".auditignore"]
    install_cmd: str = "pip install uv"
    test_cmd: list[str] = ["uv", "run", "pytest"]
    lint_check_cmd: list[str] = ["uv", "run", "ruff", "check", "--fix", "."]
    type_check_cmd: list[str] = ["uv", "run", "mypy", "src/"]
    security_check_cmd: list[str] = ["uv", "run", "bandit", "-r", "src/", "-ll"]


class AgentsConfig(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")
    # Models
    architect_model: str = "gemini-2.5-pro"
    structurer_model: str = "gemini-2.5-pro"
    coder_model: str = "gemini-2.5-pro"
    tester_model: str = "gemini-2.5-pro"
    auditor_model: str = "gemini-2.5-pro"
    qa_analyst_model: str = "gemini-2.5-flash"
    planner_model: str = "gemini-2.5-pro"

    # Prompts (Content loaded via _read_prompt)
    architect: str = Field(
        default_factory=lambda: _read_prompt("architect.md", "DEFAULT_ARCHITECT_PROMPT")
    )
    coder: str = Field(default_factory=lambda: _read_prompt("coder.md", "DEFAULT_CODER_PROMPT"))
    tester: str = Field(default_factory=lambda: _read_prompt("tester.md", "DEFAULT_TESTER_PROMPT"))
    auditor: str = Field(
        default_factory=lambda: _read_prompt("auditor.md", "DEFAULT_AUDITOR_PROMPT")
    )
    qa_analyst: str = Field(
        default_factory=lambda: _read_prompt("qa_analyst.md", "DEFAULT_QA_ANALYST_PROMPT")
    )
    structurer: str = Field(
        default_factory=lambda: _read_prompt("structurer.md", "DEFAULT_STRUCTURER_PROMPT")
    )
    planner: str = Field(
        default_factory=lambda: _read_prompt("planner.md", "DEFAULT_PLANNER_PROMPT")
    )


class PromptsConfig(BaseSettings):
    model_config = SettingsConfigDict(extra="ignore")
    property_test_template: str = Field(
        default_factory=lambda: _read_prompt("property_test_template.md", "DEFAULT_TEST_PROMPT")
    )
    # Explicit file path reference as requested
    structurer: str = "ac_cdd_core/prompts/structurer.md"


class Settings(BaseSettings):
    MAX_RETRIES: int = 10
    DUMMY_CYCLE_ID: str = "00"

    paths: PathsConfig = PathsConfig()
    jules: JulesConfig = JulesConfig()
    tools: ToolsConfig = ToolsConfig()
    sandbox: SandboxConfig = SandboxConfig()
    agents: AgentsConfig = AgentsConfig()
    prompts: PromptsConfig = PromptsConfig()

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


config = Settings()
