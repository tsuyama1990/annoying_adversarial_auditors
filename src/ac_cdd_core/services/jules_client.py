import asyncio
import json
import subprocess
import time
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

from ac_cdd_core.config import settings
from ac_cdd_core.process_runner import ProcessRunner
from ac_cdd_core.utils import logger

console = Console()

class JulesSessionError(Exception):
    pass

class JulesTimeoutError(JulesSessionError):
    pass

class JulesClient:
    """
    Client for interacting with the Jules Autonomous Agent via CLI.
    Manages session execution, polling for completion, and timeout handling.
    """

    def __init__(self) -> None:
        self.runner = ProcessRunner()
        self.executable = settings.jules.executable
        self.timeout = settings.jules.timeout_seconds
        self.polling_interval = settings.jules.polling_interval_seconds
        # Fallback if settings don't have jules_cmd
        self.cmd = getattr(settings.tools, "jules_cmd", "jules")
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
        Starts a Jules session and waits for the completion signal file.

        Args:
            session_id: The unique session identifier.
            prompt: The instruction prompt for the agent.
            files: List of file paths to load into context.
            completion_signal_file: The file path to poll for completion.

        Returns:
            The content of the completion signal file (parsed JSON).
        """
        # 1. Clean up previous signal file
        if completion_signal_file.exists():
            try:
                completion_signal_file.unlink()
            except Exception as e:
                logger.warning(f"Could not delete old signal file {completion_signal_file}: {e}")

        # 2. Construct Chat Command
        # Use configured executable (might be mock script) or 'jules'
        cmd_exe = self.executable

        cmd = [cmd_exe, "chat", "--session", session_id]

        for file_path in files:
            # Only add existing files to avoid errors
            if Path(file_path).exists():
                cmd.extend(["--file", str(file_path)])

        cmd.append(prompt)

        logger.info(f"Starting Jules Session {session_id}...")
        logger.debug(f"Command: {' '.join(cmd)}")

        # Execute Command
        try:
            # Using run_in_executor to avoid blocking event loop
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: subprocess.run(
                    cmd, check=True, capture_output=True, text=True
                )
            )
        except subprocess.CalledProcessError as e:
            logger.error(f"Jules CLI failed: {e.stderr}")
            raise JulesSessionError(f"Jules CLI failed: {e.stderr}") from e

        # 3. Poll for completion
        result = await self._wait_for_completion(
            completion_signal_file,
            timeout=timeout_override or self.timeout,
            task_name=f"Jules ({session_id})"
        )

        # 4. Sync Files (Pull)
        if "mock_jules" not in str(self.executable):
            await self._sync_files(session_id)
        else:
            logger.info("Skipping 'jules fs pull' (Mock mode)")

        return result

    async def _sync_files(self, session_id: str) -> None:
        """Pulls files from the remote Jules session."""
        cmd = [self.cmd, "fs", "pull", "--session", session_id]
        logger.info(f"Syncing files from session {session_id}...")
        try:
            # We use ProcessRunner here for async execution
            stdout, stderr, code = await self.runner.run_command(cmd, check=False)
            if code != 0:
                logger.warning(f"File sync failed (non-critical): {stderr}")
            else:
                logger.info("File sync complete.")
        except Exception as e:
            logger.warning(f"File sync error: {e}")

    async def _wait_for_completion(
        self, signal_file: Path, timeout: int, task_name: str
    ) -> dict[str, Any]:
        """
        Polls for the existence of the signal file.
        """
        start_time = time.time()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            TimeElapsedColumn(),
            transient=True,
            console=self.console
        ) as progress:
            task = progress.add_task(f"Waiting for {task_name}...", total=None)

            while True:
                elapsed = time.time() - start_time
                if elapsed > timeout:
                    raise JulesTimeoutError(
                        f"Jules session timed out after {timeout}s. "
                        f"Signal file {signal_file} not found."
                    )

                if signal_file.exists():
                    try:
                        content = signal_file.read_text(encoding="utf-8")
                        if content.strip():
                            data = json.loads(content)
                            progress.update(task, description=f"{task_name} Completed!")
                            return data  # type: ignore
                    except json.JSONDecodeError:
                        logger.warning(
                            f"Signal file {signal_file} found but contains invalid JSON."
                            " Retrying..."
                        )
                    except Exception as e:
                        logger.warning(f"Error reading signal file: {e}")

                await asyncio.sleep(self.polling_interval)
