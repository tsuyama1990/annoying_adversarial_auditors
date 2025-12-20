import json
import time
import subprocess
import asyncio
from pathlib import Path
from typing import Optional, List
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from ac_cdd_core.config import settings
from ac_cdd_core.utils import logger

class JulesClient:
    """
    Client for interacting with the Jules Autonomous Agent via CLI.
    Manages session execution, polling for completion, and timeout handling.
    """

    def __init__(self):
        self.executable = settings.jules.executable
        self.timeout = settings.jules.timeout_seconds
        self.polling_interval = settings.jules.polling_interval_seconds
        self.console = Console()

    async def run_session(
        self,
        session_id: str,
        prompt: str,
        files: List[str],
        completion_signal_file: Path
    ) -> dict:
        """
        Starts a Jules session and waits for the completion signal file.

        Args:
            session_id: The unique session identifier.
            prompt: The instruction prompt for the agent.
            files: List of file paths to load into context.
            completion_signal_file: The file path to poll for completion.

        Returns:
            The content of the completion signal file (parsed JSON).

        Raises:
            TimeoutError: If the agent does not complete within the timeout.
            RuntimeError: If the CLI command fails.
        """
        # Clean up previous signal file if it exists to avoid false positives
        if completion_signal_file.exists():
            try:
                completion_signal_file.unlink()
            except Exception as e:
                logger.warning(f"Could not delete old signal file {completion_signal_file}: {e}")

        # Construct command
        cmd = [self.executable, "chat", "--session", session_id]

        for file_path in files:
            cmd.extend(["--file", str(file_path)])

        # Add prompt as the final argument
        cmd.append(prompt)

        logger.info(f"Starting Jules Session {session_id}...")
        logger.debug(f"Command: {' '.join(cmd)}")

        # Execute Command (Async/Non-blocking from Python's perspective,
        # but the subprocess might return quickly while the agent works in background)
        try:
            # We use run_in_executor to not block the event loop
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: subprocess.run(cmd, check=True, capture_output=True, text=True)
            )
        except subprocess.CalledProcessError as e:
            logger.error(f"Jules CLI failed: {e.stderr}")
            raise RuntimeError(f"Jules CLI failed: {e.stderr}") from e

        # Poll for completion
        return await self._wait_for_completion(completion_signal_file)

    async def _wait_for_completion(self, signal_file: Path) -> dict:
        """
        Polls for the existence of the signal file.
        """
        start_time = time.time()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
            console=self.console
        ) as progress:
            task = progress.add_task(f"Waiting for Jules (Target: {signal_file.name})...", total=None)

            while True:
                elapsed = time.time() - start_time
                if elapsed > self.timeout:
                    raise TimeoutError(f"Jules session timed out after {self.timeout}s. Signal file {signal_file} not found.")

                if signal_file.exists():
                    try:
                        content = signal_file.read_text(encoding="utf-8")
                        data = json.loads(content)
                        progress.update(task, description="Jules completed task!")
                        return data
                    except json.JSONDecodeError:
                        logger.warning(f"Signal file {signal_file} found but contains invalid JSON. Retrying...")
                    except Exception as e:
                        logger.warning(f"Error reading signal file: {e}")

                await asyncio.sleep(self.polling_interval)
