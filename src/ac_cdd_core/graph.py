from pathlib import Path
from typing import Any, Literal

from langgraph.graph import END, StateGraph

from .agents import auditor_agent
from .config import settings
from .domain_models import AuditResult
from .process_runner import ProcessRunner
from .service_container import ServiceContainer
from .state import CycleState
from .utils import logger
from .services.jules_client import JulesClient
from .services.git_ops import GitManager


class GraphBuilder:
    def __init__(self, services: ServiceContainer):
        self.services = services
        self.jules_client = JulesClient()
        self.git = GitManager()

    async def init_branch_node(self, state: CycleState) -> dict[str, Any]:
        """
        Setup Git Branch.
        """
        logger.info("Phase: Init Branch")
        cycle_id = state.get("cycle_id", "init")

        # Ensure clean state
        await self.git.ensure_clean_state()

        # Create branch
        branch = await self.git.create_working_branch("ac-cdd", cycle_id)

        return {"current_phase": "branch_ready", "active_branch": branch}

    async def architect_node(self, state: CycleState) -> dict[str, Any]:
        """
        Architect Session: Generates all specs and plans.
        """
        logger.info("Phase: Architect Session")

        # Prepare Inputs
        template_path = Path(settings.paths.templates) / "ARCHITECT_INSTRUCTION.md"
        spec_path = Path(settings.paths.documents_dir) / "ALL_SPEC.md"

        if not spec_path.exists():
            return {"error": "ALL_SPEC.md not found.", "current_phase": "architect_failed"}

        instruction = template_path.read_text(encoding="utf-8")

        # Signal File
        signal_file = Path(settings.paths.documents_dir) / "plan_status.json"

        # Run Jules
        try:
            result = await self.jules_client.run_session(
                session_id=f"architect-{state.get('cycle_id')}",
                prompt=instruction,
                files=[str(spec_path), str(template_path)],
                completion_signal_file=signal_file
            )
        except Exception as e:
            logger.error(f"Architect session failed: {e}")
            return {"error": str(e), "current_phase": "architect_failed"}

        # Commit Artifacts
        await self.git.commit_changes("docs: generate system architecture and specs")

        # Extract cycles from result
        cycles = result.get("cycles", [])
        logger.info(f"Architect planned cycles: {cycles}")

        return {
            "current_phase": "architect_complete",
            "planned_cycles": cycles,
            "error": None
        }

    async def coder_node(self, state: CycleState) -> dict[str, Any]:
        """
        Coder Session: Iterates through cycles and implements them.
        """
        cycles = state.get("planned_cycles", [])
        if not cycles:
            # Fallback if state missing (e.g. restart) or manual cycle
            cycles = [state.get("cycle_id")]

        logger.info(f"Phase: Coder Session (Cycles: {cycles})")

        coder_template_path = Path(settings.paths.templates) / "CODER_INSTRUCTION.md"
        base_instruction = coder_template_path.read_text(encoding="utf-8")

        reports = []

        for cycle in cycles:
            logger.info(f"Starting Implementation for CYCLE {cycle}")

            # Prepare context files
            cycle_dir = Path(settings.paths.documents_dir) / f"CYCLE{cycle}"
            spec_file = cycle_dir / "SPEC.md"
            uat_file = cycle_dir / "UAT.md"
            arch_file = Path(settings.paths.documents_dir) / "SYSTEM_ARCHITECTURE.md"

            files = [str(coder_template_path), str(arch_file)]
            if spec_file.exists(): files.append(str(spec_file))
            if uat_file.exists(): files.append(str(uat_file))

            # Interpolate cycle_id in instruction
            instruction = base_instruction.replace("{{cycle_id}}", cycle)

            signal_file = cycle_dir / "session_report.json"

            try:
                result = await self.jules_client.run_session(
                    session_id=f"coder-{cycle}",
                    prompt=instruction,
                    files=files,
                    completion_signal_file=signal_file
                )
                reports.append(result)

                # Commit per cycle
                await self.git.commit_changes(f"feat(cycle{cycle}): implement features")

            except Exception as e:
                logger.error(f"Coder session failed for Cycle {cycle}: {e}")
                return {"error": f"Cycle {cycle} failed: {e}", "current_phase": "coder_failed"}

        return {"current_phase": "coder_complete", "coder_reports": reports}

    async def auditor_node(self, state: CycleState) -> dict[str, Any]:
        """
        Auditor: Checks git diff using existing agent.
        """
        logger.info("Phase: Auditor")

        # Get Diff
        diff = await self.git.get_diff("main") # Assuming auditing against main

        if not diff:
            logger.info("No changes to audit.")
            return {"current_phase": "audit_passed"}

        # Use existing agent
        prompt = (
            "You are a Security and Code Quality Auditor.\n"
            "Review the following git diff for critical issues.\n"
            "If approved, set is_approved=True. If rejected, list critical_issues.\n\n"
            f"GIT DIFF:\n{diff[:50000]}" # Truncate if too huge
        )

        result = await auditor_agent.run(prompt)
        audit_res: AuditResult = result.output

        if audit_res.is_approved:
            logger.info("Audit Passed.")
            return {"audit_result": audit_res, "current_phase": "audit_passed", "error": None}

        logger.warning(f"Audit Failed: {audit_res.critical_issues}")
        return {
            "audit_result": audit_res,
            "error": "Audit Failed. See Audit Result.",
            "current_phase": "audit_failed"
        }

    async def merge_node(self, state: CycleState) -> dict[str, Any]:
        """
        Merge to Main (or create PR).
        """
        logger.info("Phase: Merge")

        # In this simplistic flow, we just log.
        # In reality, we might push and create a PR.
        # But per requirements: "Merge to main branch or create PR"

        branch = await self.git.get_current_branch()
        logger.info(f"Ready to merge {branch} to main. (Automated merge disabled for safety in this demo)")

        # Optionally we could do:
        # await self.git.merge_branch("main", branch)

        return {"current_phase": "complete"}


    def build_main_graph(self) -> StateGraph[CycleState]:
        workflow = StateGraph(CycleState)

        workflow.add_node("init_branch", self.init_branch_node)
        workflow.add_node("architect", self.architect_node)
        workflow.add_node("coder", self.coder_node)
        workflow.add_node("auditor", self.auditor_node)
        workflow.add_node("merge", self.merge_node)

        # Flow
        workflow.set_entry_point("init_branch")
        workflow.add_edge("init_branch", "architect")

        def check_architect(state: CycleState) -> Literal["coder", "end"]:
            if state.get("error"): return "end"
            return "coder"

        workflow.add_conditional_edges("architect", check_architect, {"coder": "coder", "end": END})

        def check_coder(state: CycleState) -> Literal["auditor", "end"]:
            if state.get("error"): return "end"
            return "auditor"

        workflow.add_conditional_edges("coder", check_coder, {"auditor": "auditor", "end": END})

        def check_audit(state: CycleState) -> Literal["merge", "coder", "end"]:
            if state.get("error"):
                # If audit fails, we loop back to Coder?
                # The requirements didn't explicitly specify a loop back for Jules Coder,
                # but "Correction History" implies it.
                # However, JulesCoder is a "Session".
                # For now, let's fail to END to avoid infinite money burning loops with Jules.
                logger.error("Audit failed. Stopping workflow for manual review.")
                return "end"
            return "merge"

        workflow.add_conditional_edges("auditor", check_audit, {"merge": "merge", "coder": "coder", "end": END})
        workflow.add_edge("merge", END)

        return workflow

# Facade for CLI
def build_graph(services: ServiceContainer) -> StateGraph[CycleState]:
    return GraphBuilder(services).build_main_graph()
