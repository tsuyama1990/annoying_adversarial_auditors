import subprocess
import shutil
from typing import Optional
from pathlib import Path

class ToolError(Exception):
    """外部ツールの実行エラー"""
    pass

class BaseClient:
    def _run_cmd(self, cmd: list[str], input_text: Optional[str] = None) -> str:
        """コマンド実行の共通ラッパー"""
        try:
            # S603: subprocess call - check=True ensures safety against shell injection if properly args are list
            # We assume cmd is a list of strings.
            result = subprocess.run(  # noqa: S603
                cmd,
                input=input_text,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            raise ToolError(f"Command failed: {' '.join(cmd)}\nError: {e.stderr}")
        except FileNotFoundError:
            raise ToolError(f"Tool not found: {cmd[0]}. Please run 'manage.py doctor'.")

class GeminiClient(BaseClient):
    def generate_content(self, prompt: str) -> str:
        """Gemini CLI経由でコンテンツを生成"""
        # APIキーのハンドリングやリトライ処理を将来的にここに追加可能
        return self._run_cmd(["gemini", "-p", prompt])

class JulesClient(BaseClient):
    def create_session(self, prompt: str, repo: Optional[str] = None) -> str:
        """Julesセッションを作成"""
        cmd = ["jules", "new", prompt]
        if repo:
            cmd.extend(["--repo", repo])
        return self._run_cmd(cmd)

class GitClient(BaseClient):
    def get_diff(self, target: str = "HEAD") -> str:
        """Git差分を取得"""
        try:
            return self._run_cmd(["git", "diff", target])
        except ToolError:
            # git diffのエラー（差分なし等）は空文字として扱う場合
            return ""
