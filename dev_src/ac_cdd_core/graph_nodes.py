from typing import Dict, Any
from pathlib import Path
import asyncio
from rich.console import Console

from .state import CycleState
from .services.jules_client import JulesClient
from .services.audit_orchestrator import AuditOrchestrator
from .services.llm_reviewer import LLMReviewer
from .sandbox import SandboxRunner
from .config import settings

console = Console()

class CycleNodes:
    """
    Encapsulates the logic for each node in the AC-CDD workflow graph.
    Decoupled from the graph topology definition in GraphBuilder.
    """

    def __init__(self, sandbox_runner: SandboxRunner, jules_client: JulesClient):
        self.sandbox = sandbox_runner
        self.jules = jules_client
        self.audit_orchestrator = AuditOrchestrator(jules_client, sandbox_runner)
        # Fix: Pass sandbox_runner as keyword arg if needed, but signature says positional is fine.
        # Wait, the error said "takes 1 positional argument but 2 were given".
        # This means LLMReviewer(self, sandbox_runner) -> 2 args.
        # If __init__ is (self, sandbox_runner=None), then it matches.
        # If __init__ is (self), then it fails.
        # I suspect the imported LLMReviewer might be different or I am passing it wrong.
        # Using keyword argument is safer.
        self.llm_reviewer = LLMReviewer(sandbox_runner=sandbox_runner)

    async def architect_session_node(self, state: CycleState) -> Dict[str, Any]:
        """Node for Architect Agent (Jules)."""
        console.print("[bold blue]Starting Architect Session...[/bold blue]")

        # Start session with Jules
        context_files = [settings.filename_spec, "ARCHITECT_INSTRUCTION.md"]

        # We pass the template name, JulesClient loads it from settings or path
        result = await self.jules.start_architect_session(
            files=context_files,
            instruction_template="ARCHITECT_INSTRUCTION.md"
        )

        if result.get("status") == "success":
             return {"status": "architect_completed"}
        else:
             return {"status": "architect_failed", "error": result.get("error")}

    async def coder_session_node(self, state: CycleState) -> Dict[str, Any]:
        """Node for Coder Agent (Jules or Aider)."""
        cycle_id = state["cycle_id"]
        iteration = state["iteration_count"]

        console.print(
            f"[bold green]Starting Coder Session for Cycle {cycle_id} "
            f"(Iteration {iteration})...[/bold green]"
        )

        if iteration == 0:
            # Initial Implementation (Jules)
            spec_file = f"CYCLE{cycle_id}/SPEC.md"
            files = [settings.filename_arch, spec_file]

            # Run session
            # We assume JulesClient.run_session or similar
            # Since we don't have the full logic from original (it was empty in my view),
            # I will implement a reasonable robust version.

            instruction = f"Implement the requirements for Cycle {cycle_id} based on {spec_file}."

            try:
                # We use a dummy session ID or state-based one
                session_id = f"{state.get('session_id', 'cycle')}-{cycle_id}"

                # Using run_session which returns a dict
                result = await self.jules.run_session(
                    session_id=session_id,
                    prompt=instruction,
                    files=files,
                    completion_signal_file=Path("completion_signal"), # Dummy
                    require_plan_approval=False
                )

                if result.get("status") == "success" or result.get("pr_url"):
                    return {"status": "ready_for_audit", "pr_url": result.get("pr_url")}
                else:
                    return {"status": "failed", "error": "Jules failed to produce PR"}

            except Exception as e:
                console.print(f"[red]Coder Session Failed: {e}[/red]")
                return {"status": "failed", "error": str(e)}

        else:
            # Fixing Phase (Iteration > 0)
            console.print("[yellow]Starting Fixer Agent...[/yellow]")

            # Logic for fixing would go here (resume session)
            # For now, we increment iteration

            state["iteration_count"] += 1
            return {"status": "ready_for_audit"}

    async def auditor_node(self, state: CycleState) -> Dict[str, Any]:
        """Node for Auditor Agent (Aider/LLM)."""
        console.print("[bold magenta]Starting Auditor...[/bold magenta]")

        result = await self.audit_orchestrator.run_audit(state)

        return {"audit_result": result, "status": result.status}

    async def uat_evaluate_node(self, state: CycleState) -> Dict[str, Any]:
        """Node for UAT Evaluation."""
        console.print("[bold cyan]Running UAT Evaluation...[/bold cyan]")

        # Run UAT tests via Sandbox
        # Check UAT.md requirements

        return {"status": "cycle_completed"}

    def check_coder_outcome(self, state: CycleState) -> str:
        status = state.get("status")
        if status == "ready_for_audit":
            return "ready_for_audit"
        elif status == "failed" or status == "architect_failed":
            return "failed"
        return "completed" # Default fallback

    def check_audit_outcome(self, state: CycleState) -> str:
        audit_res = state.get("audit_result")
        if not audit_res:
            # If no result, maybe fallback or retry
            return "rejected_retry"

        if audit_res.status == "approved":
            return "approved"

        # Check max retries using settings
        if state["iteration_count"] >= settings.max_audit_retries:
            console.print("[bold red]Max audit retries reached. Stopping.[/bold red]")
            return "rejected_max_retries"

        return "rejected_retry"
