from pathlib import Path
from typing import Any

from pydantic_ai import Agent, RunContext

from src.ac_cdd.config import settings
from src.ac_cdd.domain_models import (
    AuditResult,
    CyclePlan,
    FileOperation,
    StructuredSpec,
    SystemArchitecture,
    UatAnalysis,
)
from src.ac_cdd.tools import semantic_code_search


def _load_file_content(filepath: str) -> str:
    path = Path(filepath)
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def _get_system_context() -> str:
    """Injects global context from ALL_SPEC.md and conventions.md if available."""
    context = []

    # Load ALL_SPEC context (Prefer Structured)
    docs_dir = Path(settings.paths.documents_dir)
    structured_spec_path = docs_dir / "ALL_SPEC_STRUCTURED.md"
    raw_spec_path = docs_dir / "ALL_SPEC.md"

    if structured_spec_path.exists():
        content = structured_spec_path.read_text(encoding="utf-8")
        context.append(f"### Project Specifications (Structured)\n{content}")
    elif raw_spec_path.exists():
        content = raw_spec_path.read_text(encoding="utf-8")
        context.append(f"### Project Specifications (Raw)\n{content}")

    # Load conventions.md
    conventions_path = Path(settings.paths.documents_dir) / "conventions.md"
    if conventions_path.exists():
        content = conventions_path.read_text(encoding="utf-8")
        context.append(f"### Coding Conventions\n{content}")

    return "\n\n".join(context)


# --- Agents ---

# Structurer Agent
structurer_agent: Agent[Any, SystemArchitecture] = Agent(
    settings.agents.structurer_model,
    system_prompt=settings.agents.structurer,
)


@structurer_agent.system_prompt
def structurer_system_prompt(ctx: RunContext[Any]) -> str:
    return _get_system_context()


# Planner Agent
planner_agent: Agent[Any, CyclePlan] = Agent(
    settings.agents.planner_model,
    system_prompt=settings.agents.planner,
    tools=[semantic_code_search],
)


@planner_agent.system_prompt
def planner_system_prompt(ctx: RunContext[Any]) -> str:
    return _get_system_context()


# Coder Agent
coder_agent: Agent[Any, list[FileOperation]] = Agent(
    settings.agents.coder_model,
    system_prompt=settings.agents.coder,
    tools=[semantic_code_search],
)


@coder_agent.system_prompt
def coder_system_prompt(ctx: RunContext[Any]) -> str:
    return _get_system_context()


# Auditor Agent
auditor_agent: Agent[Any, AuditResult] = Agent(
    settings.agents.auditor_model,
    system_prompt=settings.agents.auditor,
    # Auditor typically receives file content in prompt, but search helps for cross-file checks
    tools=[semantic_code_search],
)


@auditor_agent.system_prompt
def auditor_system_prompt(ctx: RunContext[Any]) -> str:
    return _get_system_context()


# QA Analyst Agent
qa_analyst_agent: Agent[Any, UatAnalysis] = Agent(
    settings.agents.qa_analyst_model,
    system_prompt=settings.agents.qa_analyst,
)


@qa_analyst_agent.system_prompt
def qa_analyst_system_prompt(ctx: RunContext[Any]) -> str:
    return _get_system_context()


# Architect Agent (Spec Refiner)
architect_agent: Agent[Any, StructuredSpec] = Agent(
    settings.agents.architect_model,
    system_prompt=settings.agents.architect,
)
