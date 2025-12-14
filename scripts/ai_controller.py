import typer
import subprocess
import shutil
import sys
import json
import concurrent.futures
from pathlib import Path
from typing import Optional
import os

from src.agent_interface import AgentInterface
from src.jules_api_client import JulesApiClient
from src.jules_cli_client import JulesCliClient

app = typer.Typer(help="AI Native Development Controller v2")

def get_agent_client() -> AgentInterface:
    api_key = os.getenv("JULES_API_KEY")
    if api_key:
        typer.secho("🚀 API Key found. Running in API Mode (Stateful).", fg=typer.colors.GREEN)
        return JulesApiClient(api_key)
    else:
        typer.secho("⚠️ API Key not found. Running in CLI Mode (Stateless).", fg=typer.colors.YELLOW)
        return JulesCliClient()

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

    client = get_agent_client()

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
        status = client.send_message(instructions)
        typer.secho(status, fg=typer.colors.CYAN)
    else:
        typer.secho("✅ レビュー合格！修正の必要はありません。", fg=typer.colors.GREEN)


@app.command()
def auto_fix():
    """
    テストを実行し、失敗した場合にエラーログをJulesに渡して自動修正を依頼します。
    """
    check_dependency("uv")
    client = get_agent_client()

    typer.secho("🧪 テストを実行中...", fg=typer.colors.BLUE)
    result = run_subprocess(["uv", "run", "pytest"], check=False, capture_output=True)

    if result.returncode == 0:
        typer.secho("✅ すべてのテストが通過しました。", fg=typer.colors.GREEN)
        return

    typer.secho("❌ テストが失敗しました。ログを分析して修正タスクを発行します...", fg=typer.colors.RED)
    logs = result.stdout + "\n" + result.stderr
    task_description = f"テストが失敗しました。以下のログを分析し、コードを修正してテストを通してください。\n\nLogs:\n{logs}"

    status = client.send_message(task_description)
    typer.secho(f"🚀 Julesに修正タスクを送信しました: {status}", fg=typer.colors.MAGENTA)


@app.command()
def architect(
    request: str = typer.Argument(..., help="実装したい機能の大まかな要望")
):
    """
    曖昧な要望からGeminiが仕様書を作成し、それをJulesに渡して実装を開始します。
    """
    check_dependency("gemini")
    client = get_agent_client()

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
    status = client.start_task(spec_content, session_name="Feature Implementation")
    typer.secho(status, fg=typer.colors.CYAN)


@app.command()
def triage_issues():
    """
    自分にアサインされたGitHub Issueを取得し、それぞれに対してJulesセッションを開始します。
    """
    check_dependency("gh", "GitHub CLIをインストールしてください。")
    client = get_agent_client()

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
        status = client.start_task(prompt, session_name=f"Issue #{number}")
        typer.secho(status, fg=typer.colors.CYAN)


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
    client = get_agent_client()
    tasks = [line.strip() for line in file.read_text().splitlines() if line.strip()]

    if not tasks:
        typer.secho("⚠️ ファイルにタスクが見つかりませんでした。", fg=typer.colors.YELLOW)
        return

    typer.secho(f"🚀 {len(tasks)}件のタスクを {parallel}並列で実行します...", fg=typer.colors.GREEN)

    def execute_task(task_prompt):
        typer.secho(f"▶️ タスク開始: {task_prompt[:30]}...", fg=typer.colors.BLUE)
        try:
            return client.start_task(task_prompt, session_name=task_prompt)
        except ConnectionError as e:
            return f"❌ 失敗: {task_prompt[:30]}... Error: {e}"

    with concurrent.futures.ThreadPoolExecutor(max_workers=parallel) as executor:
        future_to_task = {executor.submit(execute_task, task): task for task in tasks}
        for future in concurrent.futures.as_completed(future_to_task):
            task = future_to_task[future]
            try:
                result_message = future.result()
                if "❌" in result_message:
                    typer.secho(result_message, fg=typer.colors.RED)
                else:
                    typer.secho(f"✅ 完了: {result_message}", fg=typer.colors.GREEN)
            except Exception as exc:
                typer.secho(f"⚠️ タスク '{task[:30]}...' で予期せぬ例外が発生しました: {exc}", fg=typer.colors.RED)


@app.command()
def watch():
    """
    現在実行中のJulesリモートセッション一覧を表示します。
    """
    client = get_agent_client()
    status = client.get_status()
    typer.secho(f"👀 {status}", fg=typer.colors.BLUE)


@app.command()
def gen_contract(
    description: str = typer.Argument(..., help="作成したいデータモデルの説明")
):
    """
    自然言語の説明からPydanticモデル定義を生成し、contracts/schemas.pyに追記します。
    """
    check_dependency("gemini")

    schema_file = Path("contracts/schemas.py")
    if not schema_file.exists():
        typer.secho(f"エラー: {schema_file} が見つかりません。", fg=typer.colors.RED)
        sys.exit(1)

    prompt = (
        f"以下の説明に基づいて、PythonのPydanticモデル定義を作成してください。\n"
        f"説明: {description}\n\n"
        "条件:\n"
        "- 必要なimport文（Start with 'from pydantic ...'）を含めてください。\n"
        "- コードブロック（```python ... ```）のみを出力してください。\n"
        "- すでに存在するクラスと重複しないユニークなクラス名にしてください。\n"
    )

    typer.secho("🤖 Geminiが契約（コントラクト）を生成中...", fg=typer.colors.BLUE)

    gemini_cmd = ["gemini", "--yolo", prompt]
    gemini_process = run_subprocess(gemini_cmd, capture_output=True)
    output = gemini_process.stdout.strip()

    code_block = ""
    in_block = False
    for line in output.splitlines():
        if line.strip().startswith("```"):
            in_block = not in_block
            continue
        if in_block or (not output.startswith("```") and line.strip()):
             code_block += line + "\n"
    
    if not code_block.strip() and output.strip():
        code_block = output

    if not code_block.strip():
        typer.secho("⚠️ 有効なコードが生成されませんでした。", fg=typer.colors.YELLOW)
        return

    with open(schema_file, "a") as f:
        f.write("\n\n" + "# Generated by Gemini\n" + code_block + "\n")

    typer.secho(f"✅ {schema_file} に新しいモデルを追加しました。", fg=typer.colors.GREEN)

@app.command()
def chat(
    message: str = typer.Argument(..., help="AIエージェントに送信するメッセージ")
):
    """
    現在のアクティブなセッションに直接メッセージを送信します。
    """
    client = get_agent_client()
    typer.secho(f"💬 Sending message to agent: '{message}'", fg=typer.colors.BLUE)
    status = client.send_message(message)
    typer.secho(status, fg=typer.colors.CYAN)


if __name__ == "__main__":
    app()
