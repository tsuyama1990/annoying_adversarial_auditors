import io
import os
import tarfile
from pathlib import Path

from e2b_code_interpreter import Sandbox

from .config import settings
from .hash_utils import calculate_directory_hash
from .utils import logger


class SandboxRunner:
    """
    Executes code and commands in an E2B Sandbox for safety and isolation.
    """

    def __init__(self, sandbox_id: str | None = None, cwd: str | None = None):
        self.api_key = os.getenv("E2B_API_KEY")
        if not self.api_key:
            logger.warning("E2B_API_KEY not found. Sandbox execution will fail.")

        # Use settings for defaults if not provided
        self.cwd = cwd or settings.sandbox.cwd
        self.sandbox_id = sandbox_id
        self.sandbox: Sandbox | None = None
        self._last_sync_hash: str | None = None

    async def _get_sandbox(self) -> Sandbox:
        """Get or create a sandbox instance."""
        if self.sandbox:
            return self.sandbox

        if self.sandbox_id:
            try:
                logger.info(f"Connecting to existing sandbox: {self.sandbox_id}")
                self.sandbox = Sandbox.connect(self.sandbox_id, api_key=self.api_key)
                return self.sandbox
            except Exception as e:
                logger.warning(
                    f"Failed to connect to sandbox {self.sandbox_id}: {e}. Creating new."
                )

        logger.info("Creating new E2B Sandbox...")
        self.sandbox = Sandbox.create(
            api_key=self.api_key, template=settings.sandbox.template
        )

        # Initial setup: install UV and sync files
        if settings.sandbox.install_cmd:
            self.sandbox.commands.run(
                settings.sandbox.install_cmd, timeout=settings.sandbox.timeout
            )

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

        try:
            exec_result = sandbox.commands.run(
                command_str, cwd=self.cwd, envs=env or {}, timeout=settings.sandbox.timeout
            )
            stdout = exec_result.stdout
            stderr = exec_result.stderr
            exit_code = exec_result.exit_code or 0
        except Exception as e:
            # Handle e2b's CommandExitException which might be raised automatically
            if hasattr(e, "exit_code") and hasattr(e, "stdout") and hasattr(e, "stderr"):
                stdout = e.stdout
                stderr = e.stderr
                exit_code = e.exit_code
            else:
                raise e

        if check and exit_code != 0:
            raise RuntimeError(
                f"Command failed with code {exit_code}:\nSTDOUT: {stdout}\nSTDERR: {stderr}"
            )

        return stdout, stderr, exit_code

    async def _sync_to_sandbox(self, sandbox: Sandbox) -> None:
        """
        Uploads configured directories and files to the sandbox using a tarball for performance.
        Skips if content hasn't changed.
        """
        root = Path.cwd()
        current_hash = calculate_directory_hash(
            root, settings.sandbox.files_to_sync, settings.sandbox.dirs_to_sync
        )

        if self._last_sync_hash == current_hash:
            logger.info("Sandbox files up-to-date. Skipping sync.")
            return

        tar_buffer = io.BytesIO()

        with tarfile.open(fileobj=tar_buffer, mode="w:gz") as tar:
            # Sync individual files
            for filename in settings.sandbox.files_to_sync:
                file_path = root / filename
                if file_path.exists():
                    tar.add(file_path, arcname=filename)

            # Sync directories
            for folder in settings.sandbox.dirs_to_sync:
                local_folder = root / folder
                if not local_folder.exists():
                    continue

                for file_path in local_folder.rglob("*"):
                    if file_path.is_file():
                        # Filter generic ignored
                        if "__pycache__" in str(file_path) or ".git" in str(file_path):
                            continue

                        rel_path = file_path.relative_to(root)
                        tar.add(file_path, arcname=str(rel_path))

        tar_buffer.seek(0)

        # Upload the tarball
        remote_tar_path = f"{self.cwd}/bundle.tar.gz"
        sandbox.files.write(remote_tar_path, tar_buffer)

        # Extract
        sandbox.commands.run(
            f"tar -xzf bundle.tar.gz -C {self.cwd}", timeout=settings.sandbox.timeout
        )
        logger.info("Synced files to sandbox via tarball.")
        self._last_sync_hash = current_hash

    async def close(self) -> None:
        if self.sandbox:
            self.sandbox.kill()
            self.sandbox = None
