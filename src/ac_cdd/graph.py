from pathlib import Path
from typing import Literal

from langgraph.graph import END, StateGraph

from .agents import (
    auditor_agent,
    coder_agent,
    planner_agent,
    qa_analyst_agent,
)
from .config import settings
from .domain_models import (
    AuditResult,
    CyclePlan,
    FileCreate,
    FileOperation,
    FilePatch,
    UatAnalysis,
)
from .sandbox import SandboxRunner
from .state import CycleState
from .utils import logger

# --- Node Implementations ---


async def planner_node(state: CycleState) -> dict:
    """
    Phase 0: Planning Phase
    Generates SPEC, Schema, and UAT artifacts.
    """
    cycle_id = state["cycle_id"]
    logger.info(f"Phase: Planning (Cycle {cycle_id})")

    if state.get("plan"):
        logger.info("Plan already exists, skipping generation.")
        return {"current_phase": "planning_complete"}

    planning_prompt_path = Path(settings.paths.templates) / "CYCLE_PLANNING_PROMPT.md"
    base_prompt = ""
    if planning_prompt_path.exists():
        base_prompt = planning_prompt_path.read_text(encoding="utf-8")

    user_task = f"{base_prompt}\n\nFocus specifically on generating artifacts for CYCLE{cycle_id}."

    if state.get("error"):
        user_task += f"\n\nPREVIOUS ERROR/FEEDBACK: {state['error']}"

    result = await planner_agent.run(user_task, result_type=CyclePlan)
    plan: CyclePlan = result.output

    _save_plan_artifacts(cycle_id, plan)

    return {"plan": plan, "current_phase": "planning_complete", "error": None}


async def spec_writer_node(state: CycleState) -> dict:
    """
    Phase 3.1: Align Contracts (Sync Schema)
    Phase 3.2: Generate Property Tests
    """
    cycle_id = state["cycle_id"]
    logger.info(f"Phase: Spec Writer (Cycle {cycle_id})")

    _align_contracts(cycle_id)

    user_task = settings.prompts.property_test_template.format(cycle_id=cycle_id)

    # We construct the target path here based on convention, but verify if setting can be used.
    # The setting paths.property_tests is a directory.
    target_path = Path(settings.paths.property_tests) / f"test_cycle{cycle_id}.py"

    user_task += f"\n\nReturn the code in a file named '{target_path}'."
    prompt_with_role = f"You are a QA Engineer.\n{user_task}"

    result = await coder_agent.run(prompt_with_role, result_type=list[FileOperation])
    _apply_changes(result.output)

    return {"current_phase": "spec_written"}


async def coder_node(state: CycleState) -> dict:
    """
    Phase 3.3: Implementation
    """
    cycle_id = state["cycle_id"]
    logger.info(f"Phase: Coder (Cycle {cycle_id})")

    # Increment loop count (for safety against infinite loops)
    new_loop_count = state.get("loop_count", 0) + 1

    is_fix = state.get("error") is not None

    if is_fix:
        instructions = (
            f"Fix the implementation based on the following feedback:\n"
            f"{state['error']}\n"
            f"Analyze the stack trace or audit issues and fix the code in {settings.paths.src}/."
        )
        prompt = instructions
    else:
        # Initial Implementation: Read artifacts explicitly
        spec_path = Path(settings.paths.documents_dir) / f"CYCLE{cycle_id}/SPEC.md"
        schema_path = Path(settings.paths.contracts_dir) / f"schema_cycle{cycle_id}.py"

        spec_content = (
            spec_path.read_text(encoding="utf-8") if spec_path.exists() else "No SPEC found."
        )
        schema_content = (
            schema_path.read_text(encoding="utf-8") if schema_path.exists() else "No Schema found."
        )

        prompt = (
            f"Implement requirements based on the following SPEC and Schema:\n\n"
            f"=== SPEC ===\n{spec_content}\n\n"
            f"=== Schema ===\n{schema_content}\n\n"
            f"Implement the solution in {settings.paths.src}/."
        )

    result = await coder_agent.run(prompt, result_type=list[FileOperation])
    _apply_changes(result.output)

    return {
        "code_changes": result.output,
        "error": None,
        "current_phase": "implementation_done",
        "loop_count": new_loop_count,
    }


async def tester_node(state: CycleState) -> dict:
    """
    Phase: Testing (Property + Unit)
    Runs in E2B Sandbox.
    """
    cycle_id = state["cycle_id"]
    logger.info(f"Phase: Tester (Cycle {cycle_id})")

    sandbox = SandboxRunner(sandbox_id=state.get("sandbox_id"))

    # Use configured test command
    cmd = settings.sandbox.test_cmd

    try:
        stdout, stderr, code = await sandbox.run_command(cmd, check=False)

        if sandbox.sandbox:
            new_sandbox_id = sandbox.sandbox.sandbox_id
        else:
            new_sandbox_id = state.get("sandbox_id")

        logs = stdout + "\n" + stderr

        if code != 0:
            logger.warning("Tests Failed.")
            return {
                "test_logs": logs,
                "error": f"Tests Failed:\n{logs[-2000:]}",
                "current_phase": "testing_failed",
                "sandbox_id": new_sandbox_id,
            }

        logger.info("Tests Passed.")
        return {
            "test_logs": logs,
            "error": None,
            "current_phase": "testing_passed",
            "sandbox_id": new_sandbox_id,
        }

    except Exception as e:
        return {"error": str(e), "current_phase": "testing_failed"}


async def auditor_node(state: CycleState) -> dict:
    """
    Phase 3.4: Strict Audit
    Runs static analysis (Sandbox) and LLM Audit (Local).
    """
    logger.info("Phase: Auditor")
    sandbox = SandboxRunner(sandbox_id=state.get("sandbox_id"))

    # 1. Static Analysis in Sandbox
    errors = []

    # Lint Check (Ruff)
    out, err, code = await sandbox.run_command(settings.sandbox.lint_check_cmd, check=False)

    # Type Check (Mypy)
    out, err, code = await sandbox.run_command(settings.sandbox.type_check_cmd, check=False)
    if code != 0:
        errors.append(f"Mypy Failed:\n{out}\n{err}")

    # Security Check (Bandit)
    out, err, code = await sandbox.run_command(settings.sandbox.security_check_cmd, check=False)
    if code != 0:
        errors.append(f"Bandit Failed:\n{out}\n{err}")

    if errors:
        return {
            "audit_logs": "\n".join(errors),
            "error": "\n".join(errors),
            "audit_result": AuditResult(is_approved=False, critical_issues=errors),
            "current_phase": "audit_failed",
        }

    # 2. LLM Audit (runs locally on source files)
    user_task = f"Audit the code in {settings.paths.src}/ for Pydantic contracts and security."

    files_content = _read_src_files()
    prompt = f"{user_task}\n\n{files_content}"

    result = await auditor_agent.run(prompt, result_type=AuditResult)
    audit_res: AuditResult = result.output

    if not audit_res.is_approved:
        return {
            "audit_result": audit_res,
            "error": "Audit Failed: " + "; ".join(audit_res.critical_issues),
            "current_phase": "audit_failed",
        }

    return {"audit_result": audit_res, "error": None, "current_phase": "audit_passed"}


async def uat_node(state: CycleState) -> dict:
    """
    Phase 3.5: UAT
    Generate UAT tests, run them in Sandbox, Analyze results.
    """
    cycle_id = state["cycle_id"]
    logger.info(f"Phase: UAT (Cycle {cycle_id})")

    # 1. Generate UAT Code
    uat_path = Path(settings.paths.documents_dir) / f"CYCLE{cycle_id}/UAT.md"
    uat_content = uat_path.read_text(encoding="utf-8") if uat_path.exists() else "No UAT found."

    description = (
        f"Create Playwright tests in {settings.paths.e2e_tests}/ "
        f"based on the following UAT plan:\n\n{uat_content}\n\n"
        "REQUIREMENTS:\n"
        "- Use `unittest.mock`, `pytest-mock`, or `vcrpy` to mock external connections.\n"
        "- Output valid Python code."
    )
    result = await coder_agent.run(description, result_type=list[FileOperation])
    _apply_changes(result.output)

    # 2. Run Tests in Sandbox
    sandbox = SandboxRunner(sandbox_id=state.get("sandbox_id"))
    # We want to run ONLY e2e tests here
    cmd = settings.sandbox.test_cmd + [settings.paths.e2e_tests]

    stdout, stderr, code = await sandbox.run_command(cmd, check=False)
    logs = stdout + "\n" + stderr
    success = code == 0

    # 3. Analyze
    verdict = "PASS" if success else "FAIL"
    analyze_prompt = f"Analyze UAT logs. Verdict: {verdict}\nLogs:\n{logs[-5000:]}"

    res = await qa_analyst_agent.run(analyze_prompt, result_type=UatAnalysis)
    analysis: UatAnalysis = res.output

    # Save report
    report_path = Path(settings.paths.documents_dir) / f"CYCLE{cycle_id}" / "UAT_RESULT.md"
    report_path.write_text(
        f"# UAT {verdict}\n\n{analysis.summary}\n{analysis.behavior_analysis}", encoding="utf-8"
    )

    if not success:
        return {
            "uat_analysis": analysis,
            "error": f"UAT Failed: {analysis.summary}",
            "current_phase": "uat_failed",
        }

    return {"uat_analysis": analysis, "error": None, "current_phase": "uat_passed"}


# --- Helpers (Shared with Orchestrator) ---


def _save_plan_artifacts(cycle_id: str, plan: CyclePlan) -> None:
    cycle_dir = Path(settings.paths.documents_dir) / f"CYCLE{cycle_id}"
    cycle_dir.mkdir(parents=True, exist_ok=True)
    for artifact in [plan.spec_file, plan.schema_file, plan.uat_file]:
        p = Path(artifact.path)
        target = cycle_dir / p.name
        target.write_text(artifact.content, encoding="utf-8")
    (cycle_dir / "PLAN_THOUGHTS.md").write_text(plan.thought_process, encoding="utf-8")


def _align_contracts(cycle_id: str) -> None:
    contracts_dir = Path(settings.paths.contracts_dir)
    cycle_dir = Path(settings.paths.documents_dir) / f"CYCLE{cycle_id}"
    source = cycle_dir / "schema.py"
    target = contracts_dir / f"schema_cycle{cycle_id}.py"

    if source.exists():
        contracts_dir.mkdir(parents=True, exist_ok=True)
        import shutil

        shutil.copy(source, target)
        init = contracts_dir / "__init__.py"
        line = f"from .schema_cycle{cycle_id} import *"
        if init.exists():
            if line not in init.read_text():
                with open(init, "a") as f:
                    f.write(f"\n{line}\n")
        else:
            with open(init, "w") as f:
                f.write(f"{line}\n")


def _apply_changes(changes: list[FileOperation]) -> None:
    """Applies changes locally."""
    for op in changes:
        p = Path(op.path)
        if isinstance(op, FileCreate):
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(op.content, encoding="utf-8")
            logger.info(f"Created {p}")
        elif isinstance(op, FilePatch):
            if not p.exists():
                continue
            content = p.read_text(encoding="utf-8")
            if op.search_block in content:
                new_content = content.replace(op.search_block, op.replace_block)
                p.write_text(new_content, encoding="utf-8")
                logger.info(f"Patched {p}")
            else:
                logger.warning(f"Patch failed for {p}: block not found")


def _read_src_files() -> str:
    content = ""
    # Use settings.paths.src instead of hardcoded "src"
    for p in Path(settings.paths.src).rglob("*.py"):
        content += f"\n=== {p} ===\n{p.read_text()}"
    return content


# --- Graph Definition ---


def build_graph() -> StateGraph[CycleState]:
    workflow = StateGraph(CycleState)

    # Add Nodes
    workflow.add_node("planner", planner_node)
    workflow.add_node("spec_writer", spec_writer_node)
    workflow.add_node("coder", coder_node)
    workflow.add_node("tester", tester_node)
    workflow.add_node("auditor", auditor_node)
    workflow.add_node("uat", uat_node)

    # Define Edges
    workflow.set_entry_point("planner")
    workflow.add_edge("planner", "spec_writer")
    workflow.add_edge("spec_writer", "coder")
    workflow.add_edge("coder", "tester")

    # Conditional Edges

    def check_test_result(state: CycleState) -> Literal["auditor", "coder", "end"]:
        if state.get("error"):
            if state.get("loop_count", 0) > settings.MAX_RETRIES:
                logger.error("Max retries reached in Testing Loop.")
                return "end"
            # If tests failed, go back to coder
            return "coder"
        return "auditor"

    workflow.add_conditional_edges(
        "tester", check_test_result, {"auditor": "auditor", "coder": "coder", "end": END}
    )

    def check_audit_result(state: CycleState) -> Literal["uat", "coder", "end"]:
        if state.get("error"):
            if state.get("loop_count", 0) > settings.MAX_RETRIES:
                logger.error("Max retries reached in Audit Loop.")
                return "end"
            return "coder"
        return "uat"

    workflow.add_conditional_edges(
        "auditor", check_audit_result, {"uat": "uat", "coder": "coder", "end": END}
    )

    def check_uat_result(state: CycleState) -> Literal["end", "coder"]:
        if state.get("error"):
            if state.get("loop_count", 0) > settings.MAX_RETRIES:
                logger.error("Max retries reached in UAT Loop.")
                return "end"
            return "coder"
        return "end"

    workflow.add_conditional_edges("uat", check_uat_result, {"end": END, "coder": "coder"})

    return workflow
