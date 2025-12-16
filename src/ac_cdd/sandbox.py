import os
from pathlib import Path

from e2b_code_interpreter import Sandbox

from .utils import logger


class SandboxRunner:
    """
    Executes code and commands in an E2B Sandbox for safety and isolation.
    """

    def __init__(self, sandbox_id: str | None = None, cwd: str = "/home/user"):
        self.api_key = os.getenv("E2B_API_KEY")
        if not self.api_key:
            logger.warning("E2B_API_KEY not found. Sandbox execution will fail.")
        self.cwd = cwd
        self.sandbox_id = sandbox_id
        self.sandbox: Sandbox | None = None

    async def _get_sandbox(self) -> Sandbox:
        """Get or create a sandbox instance."""
        if self.sandbox:
            return self.sandbox

        if self.sandbox_id:
            try:
                logger.info(f"Connecting to existing sandbox: {self.sandbox_id}")
                self.sandbox = await Sandbox.connect(self.sandbox_id, api_key=self.api_key)
                return self.sandbox
            except Exception as e:
                logger.warning(
                    f"Failed to connect to sandbox {self.sandbox_id}: {e}. Creating new."
                )

        logger.info("Creating new E2B Sandbox...")
        self.sandbox = await Sandbox.create(api_key=self.api_key)

        # Initial setup: install UV and sync files
        # Note: E2B standard sandbox might not have uv.
        await self.sandbox.commands.run("pip install uv")
        await self._sync_to_sandbox(self.sandbox)

        return self.sandbox

    async def run_command(
        self, cmd: list[str], check: bool = False, env: dict[str, str] | None = None
    ) -> tuple[str, str, int]:
        """
        Runs a shell command in the sandbox.
        """
        sandbox = await self._get_sandbox()

        # Ensure latest files are there before running
        await self._sync_to_sandbox(sandbox)

        command_str = " ".join(cmd)
        logger.info(f"[Sandbox] Running: {command_str}")

        exec_result = await sandbox.commands.run(
            command_str,
            cwd=self.cwd,
            envs=env or {}
        )

        stdout = exec_result.stdout
        stderr = exec_result.stderr
        exit_code = exec_result.exit_code or 0

        if check and exit_code != 0:
            raise RuntimeError(
                f"Command failed with code {exit_code}:\nSTDOUT: {stdout}\nSTDERR: {stderr}"
            )

        return stdout, stderr, exit_code

    async def _sync_to_sandbox(self, sandbox: Sandbox) -> None:
        """
        Uploads src/ and tests/ to the sandbox.
        """
        root = Path.cwd()

        # We only sync specific source directories to avoid clutter
        dirs_to_sync = ["src", "tests", "contracts", "dev_documents"]

        # Also sync pyproject.toml and uv.lock for dependency installation
        files_to_sync = ["pyproject.toml", "uv.lock", ".auditignore"]

        for filename in files_to_sync:
            file_path = root / filename
            if file_path.exists():
                remote_path = f"{self.cwd}/{filename}"
                with open(file_path, "rb") as f:
                    try:
                        await sandbox.files.write(remote_path, f)
                    except Exception as e:
                        logger.warning(f"Failed to sync {filename}: {e}")

        for folder in dirs_to_sync:
            local_folder = root / folder
            if not local_folder.exists():
                continue

            for file_path in local_folder.rglob("*"):
                if file_path.is_file():
                    if "__pycache__" in str(file_path) or ".git" in str(file_path):
                        continue

                    rel_path = file_path.relative_to(root)
                    remote_path = f"{self.cwd}/{rel_path}"

                    try:
                        # E2B writes recursively create dirs if needed usually,
                        # but let's be safe if SDK requires it.
                        # The current SDK handles it.
                        with open(file_path, "rb") as f:
                            await sandbox.files.write(remote_path, f)
                    except Exception as e:
                        logger.warning(f"Failed to sync {rel_path}: {e}")

    async def close(self) -> None:
        if self.sandbox:
            await self.sandbox.close()
            self.sandbox = None
