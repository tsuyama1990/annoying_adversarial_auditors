
import asyncio
import os
import shutil
import subprocess
from pathlib import Path

from ac_cdd_core.config import settings
from ac_cdd_core.utils import logger

class AiderClient:
    """
    Wrapper for the 'aider' CLI tool.
    Provides methods for auditing (read-only) and fixing (edit) code.
    """

    def __init__(self) -> None:
        self.smart_model = settings.aider.smart_model
        self.fast_model = settings.aider.fast_model
        # Resolve 'aider' executable path
        self.executable = shutil.which("aider")
        if not self.executable:
            logger.warning("Aider executable not found in PATH. Ensure 'aider-chat' is installed.")
            self.executable = "aider"

    async def run_audit(self, files: list[str], instruction: str) -> str:
        """
        Run Aider in read-only mode to audit files.
        Uses FAST_MODEL.
        """
        logger.info(f"Running Aider Audit on {len(files)} files...")

        # Construct command
        cmd = [
            self.executable,
            "--model", self.fast_model,
            "--read-only",
            "--no-auto-commits",
            "--message", instruction,
        ]

        # Append files (ensure they exist)
        valid_files = [f for f in files if Path(f).exists()]
        if not valid_files:
            return "No valid files to audit."

        cmd.extend(valid_files)

        try:
            # Using run_in_executor to avoid blocking the event loop
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: subprocess.run(  # noqa: S603
                    cmd, check=False, capture_output=True, text=True, env={**os.environ}
                ),
            )

            if result.returncode != 0:
                logger.warning(f"Aider audit returned non-zero exit code: {result.stderr}")

            return result.stdout
        except Exception as e:
            logger.error(f"Aider audit failed: {e}")
            return f"Audit failed due to internal error: {e}"

    async def run_fix(self, files: list[str], instruction: str) -> str:
        """
        Run Aider in edit mode to fix issues.
        Uses SMART_MODEL.
        """
        logger.info(f"Running Aider Fix on {len(files)} files...")

        cmd = [
            self.executable,
            "--model", self.smart_model,
            "--yes",  # Auto-confirm edits
            "--no-auto-commits", # Let graph handle commits
            "--message", instruction,
        ]

        valid_files = [f for f in files if Path(f).exists()]
        if not valid_files:
            return "No valid files to fix."

        cmd.extend(valid_files)

        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: subprocess.run(  # noqa: S603
                    cmd, check=False, capture_output=True, text=True, env={**os.environ}
                ),
            )

            if result.returncode != 0:
                logger.warning(f"Aider fix returned non-zero exit code: {result.stderr}")
                return f"Fix failed: {result.stderr}"

            return result.stdout
        except Exception as e:
            logger.error(f"Aider fix failed: {e}")
            return f"Fix failed due to internal error: {e}"
