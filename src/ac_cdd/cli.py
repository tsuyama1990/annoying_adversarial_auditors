import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from ac_cdd.config import settings

# Import Orchestrator from the new package location
from ac_cdd.orchestrator import CycleOrchestrator

load_dotenv()

app = typer.Typer(help="AC-CDD: AI-Native Cycle-Based Development Orchestrator")
console = Console()

def run_cmd(cmd: list[str], input_text: str | None = None, check: bool = True) -> str:
    """外部コマンド実行ヘルパー"""
    try:
        result = subprocess.run(  # noqa: S603
            cmd,
            input=input_text,
            capture_output=True,
            text=True,
            check=check
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        typer.secho(f"Error executing command: {' '.join(cmd)}", fg=typer.colors.RED)
        typer.secho(e.stderr, fg=typer.colors.RED)
        if check:
            raise typer.Exit(code=1) from e
        return e.stdout + e.stderr

@app.command()
def init():
    """プロジェクトの初期化と依存関係チェック"""
    console.print(Panel("AC-CDD環境の初期化中...", style="bold blue"))

    # Use tools from config
    checks = [
        (settings.tools.uv_cmd, "パッケージ管理には uv が必要です。"),
        (settings.tools.gh_cmd, "PR管理には GitHub CLI (gh) が必要です。"),
        (settings.tools.jules_cmd, "AIコーディングには Jules CLI が必要です。"),
        (settings.tools.gemini_cmd, "監査には Gemini CLI が必要です。"),
    ]

    all_pass = True
    for cmd, msg in checks:
        if not shutil.which(cmd):
            console.print(f"[red]✖ {cmd} が見つかりません。[/red] {msg}")
            all_pass = False
        else:
            console.print(f"[green]✔ {cmd} が見つかりました。[/green]")

    if not Path(".env").exists():
        console.print(
            "[yellow]⚠ .env ファイルが見つかりません。.env.example から作成します...[/yellow]"
        )
        if Path(".env.example").exists():
            shutil.copy(".env.example", ".env")
            console.print(
                "[green]✔ .env を作成しました。APIキーなどを入力してください。[/green]"
            )
        else:
            console.print("[red]✖ .env.example が見つかりません。[/red]")
            all_pass = False
    else:
        console.print("[green]✔ .env ファイルを確認しました。[/green]")

    if all_pass:
        console.print(Panel("初期化完了！開発を開始できます。", style="bold green"))
    else:
        console.print(
            Panel("初期化に失敗しました。上記のエラーを確認してください。", style="bold red")
        )
        raise typer.Exit(code=1)

# --- Cycle Workflow ---

@app.command(name="new-cycle")
def new_cycle(name: str):
    """新しい開発サイクルを作成します (例: 01, 02)"""
    # Assuming 'name' corresponds to cycle_id like '01'
    cycle_id = name
    base_path = Path(settings.paths.documents_dir) / f"CYCLE{cycle_id}"
    if base_path.exists():
        console.print(f"[red]サイクル {cycle_id} は既に存在します！[/red]")
        raise typer.Exit(code=1)

    base_path.mkdir(parents=True)
    templates_dir = Path(settings.paths.documents_dir) / "templates"

    # Copy templates
    shutil.copy(templates_dir / "SPEC_TEMPLATE.md", base_path / "SPEC.md")
    shutil.copy(templates_dir / "UAT_TEMPLATE.md", base_path / "UAT.md")
    shutil.copy(templates_dir / "schema_template.py", base_path / "schema.py")

    console.print(f"[green]新しいサイクルを作成しました: CYCLE{cycle_id}[/green]")
    console.print(f"[bold]{base_path}[/bold] 内のファイルを編集してください。")

@app.command(name="start-cycle")
def start_cycle(name: str, dry_run: bool = False):
    """サイクルの自動実装・監査ループを開始します"""
    cycle_id = name
    console.print(Panel(f"サイクル {cycle_id} の自動化を開始します", style="bold magenta"))
    if dry_run:
        console.print(
            "[yellow][DRY-RUN MODE] 実際のAPI呼び出しやコミットは行われません。[/yellow]"
        )

    orchestrator = CycleOrchestrator(cycle_id, dry_run=dry_run)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("[cyan]実行中...", total=None)

        try:
            orchestrator.execute_all(progress_task=task, progress_obj=progress)
            console.print(Panel(f"サイクル {cycle_id} が正常に完了しました！", style="bold green"))
        except Exception as e:
            console.print(Panel(f"サイクル失敗: {str(e)}", style="bold red"))
            raise typer.Exit(code=1) from e

# --- Ad-hoc Workflow ---

@app.command()
def audit(repo: str = typer.Option(None, help="Target repository")):
    """
    [Strict Review] Gitの差分をGeminiに激辛レビューさせ、Julesに修正指示を出します。
    """
    if not shutil.which("gemini") or not shutil.which("jules"):
        typer.secho("Error: 'gemini' or 'jules' CLI not found.", fg=typer.colors.RED)
        raise typer.Exit(1)

    typer.echo("🔍 Fetching git diff...")
    diff_output = run_cmd(["git", "diff", "HEAD"], check=False)

    if not diff_output:
        typer.secho("No changes detected to audit.", fg=typer.colors.YELLOW)
        return

    typer.echo("🧠 Gemini is thinking (Strict Review Mode)...")
    prompt = (
        "You are a Staff Engineer at Google. Conduct a 'Strict Review' of the input diff "
        "focusing on Security, Performance, and Readability. "
        "Output ONLY specific, actionable instructions for an AI coder (Jules) as a bulleted list."
        "\n\nGit Diff:\n"
    )

    # Geminiへの問い合わせ
    gemini_instruction = run_cmd(["gemini", "-p", prompt + diff_output])

    typer.echo("🤖 Jules is taking over...")
    cmd = ["jules", "new", gemini_instruction]
    if repo:
        cmd.extend(["--repo", repo])

    jules_output = run_cmd(cmd)
    typer.secho(f"✅ Audit complete. Fix task assigned to Jules!", fg=typer.colors.GREEN)
    typer.echo(jules_output)

@app.command()
def fix():
    """
    [Auto Fix] テストを実行し、失敗した場合にJulesに修正させます。
    """
    typer.echo("🧪 Running tests with pytest...")
    # テスト実行（失敗を許容）
    output = run_cmd(["uv", "run", "pytest"], check=False)

    if "failed" not in output and "error" not in output:
         typer.secho("✨ All tests passed! Nothing to fix.", fg=typer.colors.GREEN)
         return

    typer.secho("💥 Tests failed! Invoking Jules for repairs...", fg=typer.colors.RED)

    prompt = f"Tests failed. Analyze the logs and fix the code in src/.\n\nLogs:\n{output}"
    run_cmd(["jules", "new", prompt])
    typer.secho("✅ Fix task assigned to Jules.", fg=typer.colors.GREEN)

@app.command()
def doctor():
    """環境チェック（APIキーや依存ツールの確認）"""
    tools = ["git", "uv", "gh", "jules", "gemini"]
    all_ok = True
    for tool in tools:
        path = shutil.which(tool)
        status = "✅ Found" if path else "❌ Missing"
        color = typer.colors.GREEN if path else typer.colors.RED
        if not path:
            all_ok = False
        typer.secho(f"{tool:<10}: {status}", fg=color)

    if all_ok:
        typer.secho("\nSystem is ready for AI-Native Development.", fg=typer.colors.GREEN)
    else:
        typer.secho("\nPlease install missing tools.", fg=typer.colors.RED)

if __name__ == "__main__":
    app()
