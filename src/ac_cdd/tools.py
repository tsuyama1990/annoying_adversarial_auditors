import asyncio
import shutil
import subprocess
from typing import Any

from .utils import logger


class ToolNotFoundError(Exception):
    pass


class ToolWrapper:
    def __init__(self, command: str):
        self.command = command
        if not shutil.which(command):
            raise ToolNotFoundError(f"Command '{command}' not found in PATH.")

    async def run(
        self,
        args: list[str],
        capture_output: bool = True,  # Default to capturing for async
        check: bool = True,
        text: bool = True,
    ) -> subprocess.CompletedProcess[Any]:
        full_cmd = [self.command] + args
        logger.debug(f"Running command: {' '.join(full_cmd)}")

        # Determine stdout/stderr handling
        stdout_dest = asyncio.subprocess.PIPE if capture_output else None
        stderr_dest = asyncio.subprocess.PIPE if capture_output else None

        try:
            proc = await asyncio.create_subprocess_exec(
                *full_cmd, stdout=stdout_dest, stderr=stderr_dest
            )
            stdout_data, stderr_data = await proc.communicate()

            stdout_str = stdout_data.decode() if stdout_data and text else (stdout_data or "")
            stderr_str = stderr_data.decode() if stderr_data and text else (stderr_data or "")

            if check and proc.returncode != 0:
                raise subprocess.CalledProcessError(
                    proc.returncode or 1, full_cmd, output=stdout_str, stderr=stderr_str
                )

            return subprocess.CompletedProcess(
                args=full_cmd, returncode=proc.returncode or 0, stdout=stdout_str, stderr=stderr_str
            )

        except OSError as e:
            logger.error(f"Failed to execute command '{self.command}': {e}")
            raise
