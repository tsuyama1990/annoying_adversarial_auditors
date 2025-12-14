import typer
import subprocess
import shutil
import sys
import json
import concurrent.futures
from pathlib import Path
from typing import Optional

app = typer.Typer(help="AI Native Development Controller v2")

def check_dependency(command: str, install_hint: str = ""):
    """Checks if a command exists in the PATH."""
    if not shutil.which(command):
        error_msg = f"エラー: コマンド '{command}' が見つかりません。"
        if install_hint:
            error_msg += f" {install_hint}"
        typer.secho(error_msg, fg=typer.colors.RED)
        sys.exit(1)

def run_subprocess(cmd: list[str], input_text: Optional[str] = None, check: bool = True, capture_output: bool = True) -> subprocess.CompletedProcess:
    """Runs a subprocess with error handling."""
    try:
        return subprocess.run(cmd, input=input_text, check=check, capture_output=capture_output, text=True)
    except subprocess.CalledProcessError as e:
        if check:
            typer.secho(f"コマンド実行エラー: {' '.join(cmd)}", fg=typer.colors.RED)
            if e.stderr:
                typer.secho(e.stderr, fg=typer.colors.RED)
            sys.exit(e.returncode)
        return e
    except Exception as e:
        typer.secho(f"予期せぬエラー: {str(e)}", fg=typer.colors.RED)
        sys.exit(1)

@app.command()
def strict_review():
    """
    Git Diffを取得し、Geminiに厳格なレビューを依頼し、修正が必要ならJulesにタスクを投げます。
    """
    check_dependency("git")
    check_dependency("gemini")
    check_dependency("jules")

    typer.secho("🔍 Gitの差分を取得中...", fg=typer.colors.BLUE)
    diff_process = run_subprocess(["git", "diff", "HEAD"], capture_output=True)
    diff_content = diff_process.stdout.strip()

    if not diff_content:
        typer.secho("⚠️ 変更が検出されませんでした (git diff HEAD is empty)。", fg=typer.colors.YELLOW)
        return

    prompt = (
        "入力されたdiffを厳格にレビューし、修正が必要な場合は "
        "{\"has_issues\": true, \"instructions\": \"...\"}、"
        "問題なければ {\"has_issues\": false} というJSONのみを返してください。\n\n"
        f"Diff:\n{diff_content}"
    )

    typer.secho("🤖 Geminiにレビューを依頼中...", fg=typer.colors.BLUE)

    # gemini -o json --yolo [prompt]
    # prompt is positional argument
    gemini_cmd = ["gemini", "-o", "json", "--yolo", prompt]
    gemini_process = run_subprocess(gemini_cmd, capture_output=True)

    try:
        review_data = json.loads(gemini_process.stdout.strip())
    except json.JSONDecodeError:
        typer.secho("❌ GeminiからのJSON解析に失敗しました。", fg=typer.colors.RED)
        typer.secho(f"Output: {gemini_process.stdout}", fg=typer.colors.RED)
        return

    if review_data.get("has_issues"):
        instructions = review_data.get("instructions", "")
        typer.secho("🚨 修正が必要な箇所が見つかりました。Julesセッションを開始します...", fg=typer.colors.MAGENTA)

        # Pipe instructions to jules remote new
        # Use instructions as input, set session name
        run_subprocess(
            ["jules", "remote", "new", "--session", "Strict Review Fixes"],
            input_text=instructions,
            check=False,
            capture_output=False
        )
    else:
        typer.secho("✅ レビュー合格！修正の必要はありません。", fg=typer.colors.GREEN)


@app.command()
def auto_fix():
    """
    テストを実行し、失敗した場合にエラーログをJulesに渡して自動修正を依頼します。
    """
    check_dependency("uv")
    check_dependency("jules")

    typer.secho("🧪 テストを実行中...", fg=typer.colors.BLUE)

    result = run_subprocess(["uv", "run", "pytest"], check=False, capture_output=True)

    if result.returncode == 0:
        typer.secho("✅ すべてのテストが通過しました。", fg=typer.colors.GREEN)
        return

    typer.secho("❌ テストが失敗しました。ログを分析して修正タスクを発行します...", fg=typer.colors.RED)

    logs = result.stdout + "\n" + result.stderr
    task_description = f"テストが失敗しました。以下のログを分析し、コードを修正してテストを通してください。\n\nLogs:\n{logs}"

    typer.secho("🚀 Julesに修正タスクを送信しました。", fg=typer.colors.MAGENTA)
    run_subprocess(
        ["jules", "remote", "new", "--session", "Fix Test Failures"],
        input_text=task_description,
        check=False,
        capture_output=False
    )


@app.command()
def architect(
    request: str = typer.Argument(..., help="実装したい機能の大まかな要望")
):
    """
    曖昧な要望からGeminiが仕様書を作成し、それをJulesに渡して実装を開始します。
    """
    check_dependency("gemini")
    check_dependency("jules")

    prompt = (
        f"以下の要望から詳細な要件定義書（Markdown形式）を作成し、JSONの `content` フィールドに入れて返してください。\n"
        f"要望: {request}\n\n"
        "Output format: {\"content\": \"...markdown...\"}"
    )

    typer.secho("📐 Geminiが仕様を策定中...", fg=typer.colors.BLUE)

    gemini_cmd = ["gemini", "-o", "json", "--yolo", prompt]
    gemini_process = run_subprocess(gemini_cmd, capture_output=True)

    try:
        spec_data = json.loads(gemini_process.stdout.strip())
        spec_content = spec_data.get("content", "")
    except json.JSONDecodeError:
        typer.secho("❌ GeminiからのJSON解析に失敗しました。", fg=typer.colors.RED)
        return

    if not spec_content:
        typer.secho("⚠️ 仕様書の内容が空でした。", fg=typer.colors.YELLOW)
        return

    typer.secho("📋 仕様書が完成しました。実装を開始します...", fg=typer.colors.GREEN)

    run_subprocess(
        ["jules", "remote", "new", "--session", "Feature Implementation"],
        input_text=spec_content,
        check=False,
        capture_output=False
    )


@app.command()
def triage_issues():
    """
    自分にアサインされたGitHub Issueを取得し、それぞれに対してJulesセッションを開始します。
    """
    check_dependency("gh", "GitHub CLIをインストールしてください。")
    check_dependency("jules")

    typer.secho("📥 担当Issueを取得中...", fg=typer.colors.BLUE)

    cmd = ["gh", "issue", "list", "--assignee", "@me", "--json", "number,title,body"]
    result = run_subprocess(cmd, capture_output=True)

    try:
        issues = json.loads(result.stdout)
    except json.JSONDecodeError:
        typer.secho("❌ GitHub IssueのJSON解析に失敗しました。", fg=typer.colors.RED)
        sys.exit(1)

    if not issues:
        typer.secho("⚠️ 担当Issueは見つかりませんでした。", fg=typer.colors.YELLOW)
        return

    typer.secho(f"🔍 {len(issues)}件のIssueが見つかりました。順次セッションを開始します...", fg=typer.colors.GREEN)

    for issue in issues:
        number = issue.get("number")
        title = issue.get("title")
        body = issue.get("body")

        prompt = f"Issue #{number}: {title}\n\n{body}"
        typer.secho(f"🚀 Issue #{number} の処理を開始...", fg=typer.colors.BLUE)

        run_subprocess(
            ["jules", "remote", "new", "--session", f"Issue #{number}"],
            input_text=prompt,
            check=False,
            capture_output=False
        )


@app.command()
def implement_plan(
    file: Path = typer.Argument(
        Path("documents/TODO.md"),
        help="タスクリストファイルのパス",
        exists=True,
        dir_okay=False,
        readable=True
    ),
    parallel: int = typer.Option(5, help="同時実行タスク数")
):
    """
    TODOリストファイルを読み込み、各行について並列でJulesセッションを開始します。
    """
    check_dependency("jules")

    tasks = [line.strip() for line in file.read_text().splitlines() if line.strip()]

    if not tasks:
        typer.secho("⚠️ ファイルにタスクが見つかりませんでした。", fg=typer.colors.YELLOW)
        return

    typer.secho(f"🚀 {len(tasks)}件のタスクを {parallel}並列で実行します...", fg=typer.colors.GREEN)

    def execute_task(task_prompt):
        typer.secho(f"▶️ タスク開始: {task_prompt[:30]}...", fg=typer.colors.BLUE)
        try:
            # Using jules remote new, passing prompt via stdin (pipe) as requested in v2 spec
            # Using prompt as session name for clarity, sanitized slightly
            session_name = task_prompt[:50].replace(" ", "_")
            subprocess.run(
                ["jules", "remote", "new", "--session", session_name],
                input=task_prompt,
                text=True,
                check=True,
                capture_output=False # Let jules output status if it wants, or could suppress
            )
            return f"✅ 完了: {task_prompt[:30]}..."
        except subprocess.CalledProcessError:
            return f"❌ 失敗: {task_prompt[:30]}..."

    with concurrent.futures.ThreadPoolExecutor(max_workers=parallel) as executor:
        future_to_task = {executor.submit(execute_task, task): task for task in tasks}
        for future in concurrent.futures.as_completed(future_to_task):
            task = future_to_task[future]
            try:
                data = future.result()
                typer.secho(data)
            except Exception as exc:
                typer.secho(f"⚠️ タスク例外発生: {exc}", fg=typer.colors.RED)


@app.command()
def watch():
    """
    現在実行中のJulesリモートセッション一覧を表示します。
    """
    check_dependency("jules")

    typer.secho("👀 リモートセッションを監視中...", fg=typer.colors.BLUE)
    run_subprocess(["jules", "remote", "list", "--session"], check=False, capture_output=False)


if __name__ == "__main__":
    app()
