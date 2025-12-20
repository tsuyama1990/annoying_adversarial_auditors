import asyncio
import json
import os
import shutil
from pathlib import Path

import logfire
import typer
from dotenv import load_dotenv
from langgraph.checkpoint.memory import MemorySaver
from rich.console import Console
from rich.panel import Panel

from ac_cdd_core.config import settings
from ac_cdd_core.graph import GraphBuilder
from ac_cdd_core.service_container import ServiceContainer
from ac_cdd_core.services.project import ProjectManager

load_dotenv()

# Initialize Logfire
if os.getenv("LOGFIRE_TOKEN"):
    logfire.configure()

app = typer.Typer(help="AC-CDD: AI-Native Cycle-Based Development Orchestrator")
console = Console()

# Instantiate global services
services = ServiceContainer.default()
project_manager = ProjectManager()

# --- Common Utilities ---

async def _run_graph(graph, initial_state: dict, title: str, thread_id: str) -> dict:
    """
    Generic graph runner. Returns the final state.
    """
    checkpointer = MemorySaver()
    app = graph.compile(checkpointer=checkpointer)
    config = {"configurable": {"thread_id": thread_id}}

    console.print(Panel(f"Running: {title}", style="bold magenta"))

    final_state = initial_state

    try:
        async for event in app.astream(initial_state, config=config):
            for node_name, state_update in event.items():
                phase = state_update.get("current_phase", node_name)
                console.print(f"[cyan]▶ Node: {node_name} -> {phase}[/cyan]")

                if state_update.get("error"):
                    err_msg = state_update["error"]
                    console.print(f"[red]Error in {node_name}:[/red] {err_msg}")

        final_state = app.get_state(config)

        if not final_state.next:
            console.print(Panel(f"{title} Completed Successfully!", style="bold green"))
        else:
            console.print(f"[yellow]{title} paused at {final_state.next}[/yellow]")

        return final_state.values

    except Exception as e:
        console.print(Panel(f"Failure in {title}: {str(e)}", style="bold red"))
        return {"error": str(e)}

# --- New Commands ---

@app.command(name="gen-cycles")
def gen_cycles() -> None:
    """
    [Design Phase] Architect Graphを実行し、設計書と計画を生成します。
    """
    asyncio.run(_gen_cycles_async())

async def _gen_cycles_async() -> None:
    graph_builder = GraphBuilder(services)
    arch_graph = graph_builder.build_architect_graph()

    initial_state = {
        "cycle_id": "design",
        "current_phase": "start",
        "error": None,
    }

    await _run_graph(arch_graph, initial_state, "Architect Session", "arch-thread")


@app.command(name="run-cycle")
def run_cycle(
    cycle_id: str | None = typer.Argument(None, help="Target Cycle ID (e.g. 01)"),
    auto: bool = typer.Option(False, "--auto", help="Run all cycles sequentially from plan"),
) -> None:
    """
    [Implementation Phase] Coder Graphを実行し、実装・テスト・UATを行います。
    """
    if not cycle_id and not auto:
        console.print("[red]Error: Must specify CYCLE_ID or --auto[/red]")
        raise typer.Exit(code=1)

    asyncio.run(_run_cycle_async(cycle_id, auto))

async def _run_cycle_async(cycle_id: str | None, auto: bool) -> None:
    graph_builder = GraphBuilder(services)
    coder_graph = graph_builder.build_coder_graph()

    cycles_to_run = []

    if auto:
        # Load from plan_status.json
        plan_path = Path(settings.paths.documents_dir) / "plan_status.json"
        if not plan_path.exists():
            console.print("[red]plan_status.json not found. Run gen-cycles first.[/red]")
            return

        try:
            plan = json.loads(plan_path.read_text(encoding="utf-8"))
            cycles_to_run = plan.get("cycles", [])
            console.print(f"[green]Auto-detected cycles: {cycles_to_run}[/green]")
        except Exception as e:
            console.print(f"[red]Failed to read plan: {e}[/red]")
            return
    else:
        cycles_to_run = [cycle_id]

    for cid in cycles_to_run:
        console.print(Panel(f"Starting Cycle {cid}", style="bold blue"))

        initial_state = {
            "cycle_id": cid,
            "current_phase": "start",
            "error": None,
        }

        # Use unique thread ID per cycle to prevent state pollution
        thread_id = f"coder-{cid}"

        result_state = await _run_graph(
            coder_graph, initial_state, f"Coder Session (Cycle {cid})", thread_id
        )

        if result_state.get("error"):
            console.print(f"[red]Cycle {cid} Failed: {result_state['error']}[/red]")
            if auto:
                console.print("[red]Auto-mode stopped due to failure.[/red]")
                break
        else:
            console.print(f"[green]Cycle {cid} Passed![/green]")


# --- Legacy / Support Commands ---

@app.command()
def init() -> None:
    """Initialize project."""
    # (Simplified init for brevity, keeping existing logic concept)
    console.print(Panel("Initializing...", style="bold blue"))
    if not Path(".env").exists():
        console.print("[yellow].env missing. Create it first.[/yellow]")

@app.command()
def doctor() -> None:
    """Check environment."""
    checks = [settings.tools.uv_cmd, settings.tools.gh_cmd, settings.tools.audit_cmd]
    for cmd in checks:
        res = shutil.which(cmd)
        console.print(f"{cmd}: {'OK' if res else 'MISSING'}")

def friendly_error_handler() -> None:
    try:
        app()
    except Exception as e:
        console.print(Panel(f"An unexpected error occurred: {str(e)}", style="bold red"))
        if os.getenv("DEBUG"):
            console.print_exception()
        raise typer.Exit(code=1) from e

if __name__ == "__main__":
    friendly_error_handler()
