import typer
import subprocess
import shutil
import sys
from pathlib import Path
from typing import Optional

app = typer.Typer(help="AC-CDD: AI-Native Cycle-Based Development Orchestrator")

def run_cmd(cmd: list[str], input_text: Optional[str] = None, check: bool = True) -> str:
    """外部コマンド実行ヘルパー"""
    try:
        result = subprocess.run(
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
            raise typer.Exit(code=1)
        return e.stdout + e.stderr

# --- Cycle Workflow (Auditで評価されていた既存ロジックのプレースホルダ) ---
@app.command()
def new_cycle(name: str):
    """新しい開発サイクルを作成します (Cycle XX)"""
    typer.echo(f"Creating new cycle: {name}...")
    # ここにCycleOrchestratorの呼び出しロジックが入る想定
    # from .orchestrator import CycleOrchestrator
    # CycleOrchestrator().create_cycle(name)

@app.command()
def start_cycle(name: str):
    """サイクルの実装ループを開始します"""
    typer.echo(f"Starting cycle: {name}...")
    # CycleOrchestrator().run_cycle(name)


# --- Ad-hoc Workflow (Auditで欠落していると指摘された機能) ---

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
    # Note: gemini CLIの仕様に合わせて引数渡しに変更
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
        if not path: all_ok = False
        typer.secho(f"{tool:<10}: {status}", fg=color)

    if all_ok:
        typer.secho("\nSystem is ready for AI-Native Development.", fg=typer.colors.GREEN)
    else:
        typer.secho("\nPlease install missing tools.", fg=typer.colors.RED)

if __name__ == "__main__":
    app()
