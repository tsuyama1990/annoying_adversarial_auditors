import asyncio
import json
import re
import subprocess
from pathlib import Path
from typing import Any

from ac_cdd_core.config import settings
from ac_cdd_core.process_runner import ProcessRunner
from ac_cdd_core.utils import logger
from rich.console import Console

console = Console()

class JulesSessionError(Exception):
    pass

class JulesTimeoutError(JulesSessionError):
    pass

class JulesClient:
    """
    Client for interacting with the Jules Autonomous Agent via CLI.
    Manages session execution, processing output, and supervisor loop.
    """

    def __init__(self) -> None:
        self.runner = ProcessRunner()
        self.executable = settings.jules.executable
        self.timeout = settings.jules.timeout_seconds
        self.max_loops = 10
        self.console = Console()

    async def run_session(
        self,
        session_id: str,
        prompt: str,
        files: list[str],
        completion_signal_file: Path,
        timeout_override: int | None = None
    ) -> dict[str, Any]:
        """
        Starts a Jules session, parses output to create files, and loops until completion.

        Args:
            session_id: The unique session identifier.
            prompt: The instruction prompt for the agent.
            files: List of file paths to load into context.
            completion_signal_file: The file path that signals completion (e.g., plan_status.json).

        Returns:
            The content of the completion signal file (parsed JSON).
        """
        # 1. Clean up previous signal file
        if completion_signal_file.exists():
            try:
                completion_signal_file.unlink()
            except Exception as e:
                logger.warning(f"Could not delete old signal file {completion_signal_file}: {e}")

        current_prompt = prompt
        loop_count = 0
        max_loops = self.max_loops

        while loop_count < max_loops:
            loop_count += 1
            logger.info(f"Jules Session {session_id} - Loop {loop_count}/{max_loops}")

            # 2. Execute Chat Command
            stdout = await self._execute_chat(
                session_id,
                current_prompt,
                files if loop_count == 1 else []
            )

            # 3. Parse and Save Files
            self._parse_and_save(stdout)

            # 4. Check for Completion
            if completion_signal_file.exists():
                try:
                    content = completion_signal_file.read_text(encoding="utf-8")
                    if content.strip():
                        return json.loads(content)
                except Exception as e:
                    logger.warning(f"Error reading signal file: {e}")

            # 5. Prepare for Next Loop (Continue)
            logger.info(
                f"Signal file {completion_signal_file} not found. Requesting continuation..."
            )
            current_prompt = (
                "CONTINUE: plan_status.json not found. "
                "Please continue outputting the remaining files in the FILENAME format."
            )

        raise JulesTimeoutError(
            f"Jules session reached max loops ({max_loops}) "
            f"without generating {completion_signal_file}"
        )

    async def _execute_chat(self, session_id: str, prompt: str, files: list[str]) -> str:
        cmd_exe = self.executable
        cmd = [cmd_exe, "chat", "--session", session_id]

        for file_path in files:
            if Path(file_path).exists():
                cmd.extend(["--file", str(file_path)])

        cmd.append(prompt)

        try:
             # Using run_in_executor to avoid blocking event loop
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: subprocess.run(  # noqa: S603
                    cmd, check=True, capture_output=True, text=True
                ),
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            logger.error(f"Jules CLI failed: {e.stderr}")
            raise JulesSessionError(f"Jules CLI failed: {e.stderr}") from e

    def _parse_and_save(self, text: str) -> None:
        r"""
        Parses text for FILENAME blocks and writes them to disk.
        Regex: FILENAME:\s*([^\n]+)\n```\w*\n(.*?)```
        """
        pattern = re.compile(r"FILENAME:\s*([^\n]+)\n```\w*\n(.*?)```", re.DOTALL)

        matches = pattern.findall(text)
        if not matches:
            logger.info("No file blocks found in output.")
            return

        for filename, content in matches:
            filename = filename.strip()
            file_path = Path(filename)

            # Ensure directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)

            try:
                file_path.write_text(content, encoding="utf-8")
                logger.info(f"[System] Saved: {filename}")
            except Exception as e:
                logger.error(f"Failed to save {filename}: {e}")
