import asyncio
import os
import shutil
import sqlite3
from pathlib import Path

import logfire
import typer
from ac_cdd_core.config import settings
from ac_cdd_core.graph import GraphBuilder
from ac_cdd_core.service_container import ServiceContainer
from ac_cdd_core.services.project import ProjectManager
from dotenv import load_dotenv
from langgraph.checkpoint.memory import MemorySaver
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

load_dotenv()

# Initialize Logfire
if os.getenv("LOGFIRE_TOKEN"):
    logfire.configure()

app = typer.Typer(help="AC-CDD: AI-Native Cycle-Based Development Orchestrator")
console = Console()

# Instantiate global services (CLI is the entry point)
services = ServiceContainer.default()
project_manager = ProjectManager()


@app.command()
def init() -> None:
    """Initialize project and check dependencies."""
    console.print(Panel("Initializing AC-CDD Environment...", style="bold blue"))

    checks = [
        (settings.tools.uv_cmd, "Package manager 'uv' is required."),
        (settings.tools.gh_cmd, "GitHub CLI 'gh' is required for PRs."),
        (settings.tools.audit_cmd, "Bandit is required for auditing."),
    ]

    all_pass = True
    for cmd, msg in checks:
        if not shutil.which(cmd):
            console.print(f"[red]✖ {cmd} not found.[/red] {msg}")
            all_pass = False
        else:
            console.print(f"[green]✔ {cmd} found.[/green]")

    if not Path(".env").exists():
        console.print(
            "[yellow]⚠ .env file not found. Starting setup...[/yellow]"
        )

        env_content = ""
        env_template = Path(".env.example")
        if not env_template.exists():
            env_template = Path(settings.paths.templates) / ".env.example"

        if env_template.exists():
            with open(env_template, encoding="utf-8") as f:
                for line in f:
                    if line.strip() and not line.startswith("#"):
                        key = line.split("=")[0].strip()
                        default_val = line.split("=")[1].strip() if "=" in line else ""
                        value = typer.prompt(f"Enter value for {key}", default=default_val)
                        env_content += f"{key}={value}\n"
                    else:
                        env_content += line

            with open(".env", "w", encoding="utf-8") as f:
                f.write(env_content)
            console.print("[green]✔ Created .env[/green]")
        else:
            console.print("[red]✖ .env.example not found.[/red]")
            all_pass = False
    else:
        console.print("[green]✔ .env file checked.[/green]")

    if all_pass:
        console.print(Panel("Initialization Complete! Ready to develop.", style="bold green"))
    else:
        console.print(
            Panel("Initialization failed. Check errors above.", style="bold red")
        )
        raise typer.Exit(code=1)


async def _run_graph(graph, initial_state: dict, title: str, thread_id: str) -> None:
    """Generic graph runner with progress UI."""
    # Use MemorySaver for simplicity and robustness in this demo environment
    checkpointer = MemorySaver()

    # Compile
    app = graph.compile(checkpointer=checkpointer)

    config = {"configurable": {"thread_id": thread_id}}

    console.print(Panel(f"Running: {title}", style="bold magenta"))

    try:
        # We run the graph until it finishes
        # JulesClient handles its own progress bar for long running tasks.
        # Here we just show a spinner for graph transitions.

        async for event in app.astream(initial_state, config=config):
            for node_name, state_update in event.items():
                phase = state_update.get("current_phase", node_name)

                # Print phase transition
                console.print(f"[cyan]▶ Node: {node_name} -> {phase}[/cyan]")

                if state_update.get("error"):
                    err_msg = state_update["error"]
                    console.print(f"[red]Error in {node_name}:[/red] {err_msg}")

        # Check execution status
        snapshot = await app.get_state(config)

        # If we reached END, snapshot.next is empty
        if not snapshot.next:
            console.print(Panel("Workflow Completed Successfully!", style="bold green"))
        else:
            console.print(f"[yellow]Workflow paused at {snapshot.next}[/yellow]")

    except Exception as e:
        console.print(Panel(f"Failure: {str(e)}", style="bold red"))
        # raise e # Uncomment for debug


@app.command(name="run-cycle")
def run_cycle(
    cycle_id: str = typer.Option("01", help="Cycle ID to start with (if manual)"),
    goal: str = typer.Option(None, help="Optional goal override"),
) -> None:
    """
    Starts the Autonomous Development Cycle using Jules.
    Graph: Init -> Architect -> Coder -> Auditor -> Merge
    """
    asyncio.run(_run_cycle_async(cycle_id, goal))


async def _run_cycle_async(cycle_id: str, goal: str | None) -> None:
    # Ensure RAG index? Not strictly needed for Jules external session,
    # but good if we want to use local tools later.
    # Skipping for now to focus on Jules.

    graph_builder = GraphBuilder(services)
    main_graph = graph_builder.build_main_graph()

    initial_state = {
        "cycle_id": cycle_id,
        "current_phase": "start",
        "error": None,
        "goal": goal,
    }

    # Use a fixed thread_id for this project run or unique?
    # Let's use 'project-run' to allow resuming if needed, or timestamp.
    # For now, unique per run to avoid state conflicts during testing.
    import time
    thread_id = f"run-{int(time.time())}"

    await _run_graph(main_graph, initial_state, f"AC-CDD Run (Start Cycle: {cycle_id})", thread_id)


def friendly_error_handler() -> None:
    try:
        app()
    except Exception as e:
        console.print(Panel(f"An unexpected error occurred: {str(e)}", style="bold red"))
        is_debug = os.getenv("DEBUG")

        if is_debug:
            console.print_exception()
        else:
            console.print("Run with DEBUG=1 environment variable to see full traceback.")
        raise typer.Exit(code=1) from e


if __name__ == "__main__":
    friendly_error_handler()
