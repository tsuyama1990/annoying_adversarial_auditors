import subprocess
from typing import Optional, Any
import shutil
import sys
import typer

from src.agent_interface import AgentInterface

class JulesCliClient(AgentInterface):
    """
    Agent interface implementation for the Jules CLI.
    This client executes Jules commands as subprocesses.
    """

    def __init__(self):
        if not shutil.which("jules"):
            typer.secho(
                "エラー: 'jules' コマンドが見つかりません。CLIモードでの実行には Jules CLI が必要です。",
                fg=typer.colors.RED
            )
            sys.exit(1)

    def _run_subprocess(self, cmd: list[str], input_text: Optional[str] = None) -> subprocess.CompletedProcess:
        """
        Runs a subprocess, allowing output to stream to the console.
        """
        return subprocess.run(
            cmd,
            input=input_text,
            text=True,
            check=False,
            capture_output=False
        )

    def start_task(self, prompt: str, **kwargs: Any) -> str:
        """
        Starts a new task using `jules remote new`.
        """
        session_name = kwargs.get("session_name", "Jules CLI Session")
        sanitized_name = session_name[:50].replace(" ", "_")
        cmd = ["jules", "remote", "new", "--session", sanitized_name]

        try:
            result = self._run_subprocess(cmd, input_text=prompt)
            result.check_returncode()
            return f"CLI task '{sanitized_name}' started successfully."
        except subprocess.CalledProcessError as e:
            raise ConnectionError(f"CLI task '{sanitized_name}' failed.") from e

    def send_message(self, prompt: str, **kwargs: Any) -> str:
        """
        Falls back to starting a new task, as CLI mode is stateless.
        """
        warning = "⚠️ CLI mode does not support session continuation. Starting a new task instead."
        follow_up_session_name = "Jules CLI Follow-up Task"
        status = self.start_task(prompt, session_name=follow_up_session_name, **kwargs)
        return f"{warning}\n{status}"

    def get_status(self) -> str:
        """
        Executes `jules remote list` to show current session statuses.
        """
        cmd = ["jules", "remote", "list", "--session"]
        result = self._run_subprocess(cmd)
        if result.returncode == 0:
            return "Command `jules remote list` executed successfully."
        else:
            return "Command `jules remote list` failed."
