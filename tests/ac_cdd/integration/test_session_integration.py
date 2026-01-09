from unittest.mock import AsyncMock, patch

import pytest
from src.ac_cdd_core.services.git_ops import GitManager
from src.ac_cdd_core.session_manager import SessionManager


@pytest.mark.asyncio
async def test_session_manager_integration():
    """Tests the integration between the SessionManager and GitManager."""
    with patch(
        "src.ac_cdd_core.utils.command_runner.CommandRunner.run_command", new_callable=AsyncMock
    ) as mock_run:
        mock_run.return_value = ("", "", 0)

        git_manager = GitManager()
        session_manager = SessionManager(git_manager)

        # Create a new manifest
        manifest = await session_manager.create_manifest("test-session", "dev/test-session")

        # Save the manifest
        await session_manager.save_manifest(manifest, "Test commit")

        # Load the manifest
        loaded_manifest = await session_manager.load_manifest()

        assert loaded_manifest is not None
        assert loaded_manifest.project_session_id == "test-session"
        assert loaded_manifest.integration_branch == "dev/test-session"
