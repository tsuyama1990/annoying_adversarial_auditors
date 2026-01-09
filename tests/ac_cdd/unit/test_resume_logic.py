from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from src.ac_cdd_core.domain_models import CycleManifest

from src.ac_cdd_core.graph_nodes import CycleNodes


@pytest.mark.asyncio
class TestResumeLogic:
    @pytest.fixture
    def mock_dependencies(self) -> tuple[MagicMock, MagicMock]:
        """Fixture to create mock sandbox and jules services."""
        sandbox = MagicMock()
        jules = MagicMock()
        jules.wait_for_completion = AsyncMock()
        jules.run_session = AsyncMock()
        return sandbox, jules

    @patch("src.ac_cdd_core.graph_nodes.SessionManager")
    async def test_hot_resume_active_success(
        self, mock_session_manager_cls: MagicMock, mock_dependencies: tuple[MagicMock, MagicMock]
    ) -> None:
        """
        Tests the hot resume logic.
        If a Jules session ID exists in the manifest, the coder_session_node should resume that session
        and wait for its completion. This test covers the success scenario.
        """
        sandbox, jules = mock_dependencies
        nodes = CycleNodes(sandbox, jules)

        # Setup Manifest with an existing Jules Session ID
        mock_session_manager = mock_session_manager_cls.return_value
        cycle = CycleManifest(id="01", jules_session_id="jules-existing-123")
        mock_session_manager.get_cycle = AsyncMock(return_value=cycle)

        # Mock Jules Client to return a successful completion status
        jules.wait_for_completion.return_value = {"status": "success", "pr_url": "http://pr"}

        state = {"cycle_id": "01", "iteration_count": 1, "resume_mode": True}

        # Execute the node
        result = await nodes.coder_session_node(state)

        # Assert that the existing session was awaited and no new session was started
        jules.wait_for_completion.assert_awaited_once_with("jules-existing-123")
        jules.run_session.assert_not_awaited()
        assert result["status"] == "ready_for_audit"
        assert result["pr_url"] == "http://pr"

    @patch("src.ac_cdd_core.graph_nodes.SessionManager")
    async def test_hot_resume_active_failure(
        self, mock_session_manager_cls: MagicMock, mock_dependencies: tuple[MagicMock, MagicMock]
    ) -> None:
        """
        Tests the hot resume logic.
        If a Jules session ID exists in the manifest, the coder_session_node should resume that session
        and wait for its completion. This test covers the failure scenario.
        """
        sandbox, jules = mock_dependencies
        nodes = CycleNodes(sandbox, jules)

        # Setup Manifest with an existing Jules Session ID
        mock_session_manager = mock_session_manager_cls.return_value
        cycle = CycleManifest(id="01", jules_session_id="jules-existing-123")
        mock_session_manager.get_cycle = AsyncMock(return_value=cycle)

        # Mock Jules Client to return a failure completion status
        jules.wait_for_completion.return_value = {"status": "failure"}

        state = {"cycle_id": "01", "iteration_count": 1, "resume_mode": True}

        # Execute the node
        result = await nodes.coder_session_node(state)

        # Assert that the existing session was awaited and no new session was started
        jules.wait_for_completion.assert_awaited_once_with("jules-existing-123")
        jules.run_session.assert_not_awaited()
        assert result["status"] == "failure"

    @patch("src.ac_cdd_core.graph_nodes.SessionManager")
    async def test_fallback_to_new_session_and_persist_success(
        self, mock_session_manager_cls: MagicMock, mock_dependencies: tuple[MagicMock, MagicMock]
    ) -> None:
        """
        Tests the fallback logic to create a new session.
        If no Jules session ID exists in the manifest, a new session should be started and its ID
        should be immediately persisted to the manifest. This test covers the success scenario.
        """
        sandbox, jules = mock_dependencies
        nodes = CycleNodes(sandbox, jules)

        # Setup Manifest with NO existing Jules Session ID
        mock_session_manager = mock_session_manager_cls.return_value
        cycle = CycleManifest(id="01", jules_session_id=None)
        mock_session_manager.get_cycle = AsyncMock(return_value=cycle)
        mock_session_manager.update_cycle_state = AsyncMock()

        # Mock Jules Client to return a new session
        jules.run_session.return_value = {
            "session_name": "jules-new-456",
            "status": "success",
            "pr_url": "http://pr-new",
        }

        state = {"cycle_id": "01", "iteration_count": 1, "resume_mode": True}

        # Execute the node
        result = await nodes.coder_session_node(state)

        # Assert that a new session was started
        jules.run_session.assert_awaited_once()
        assert jules.run_session.await_args.kwargs["require_plan_approval"] is True

        # Verify that the new session ID was immediately persisted
        mock_session_manager.update_cycle_state.assert_awaited_with(
            "01", jules_session_id="jules-new-456", status="in_progress"
        )

        assert result["status"] == "ready_for_audit"

    @patch("src.ac_cdd_core.graph_nodes.SessionManager")
    async def test_fallback_to_new_session_and_persist_failure(
        self, mock_session_manager_cls: MagicMock, mock_dependencies: tuple[MagicMock, MagicMock]
    ) -> None:
        """
        Tests the fallback logic to create a new session.
        If no Jules session ID exists in the manifest, a new session should be started and its ID
        should be immediately persisted to the manifest. This test covers the failure scenario.
        """
        sandbox, jules = mock_dependencies
        nodes = CycleNodes(sandbox, jules)

        # Setup Manifest with NO existing Jules Session ID
        mock_session_manager = mock_session_manager_cls.return_value
        cycle = CycleManifest(id="01", jules_session_id=None)
        mock_session_manager.get_cycle = AsyncMock(return_value=cycle)
        mock_session_manager.update_cycle_state = AsyncMock()

        # Mock Jules Client to return a new session that fails
        jules.run_session.return_value = {
            "session_name": "jules-new-456",
            "status": "failure",
        }

        state = {"cycle_id": "01", "iteration_count": 1, "resume_mode": True}

        # Execute the node
        result = await nodes.coder_session_node(state)

        # Assert that a new session was started
        jules.run_session.assert_awaited_once()
        assert jules.run_session.await_args.kwargs["require_plan_approval"] is True

        # Verify that the new session ID was immediately persisted
        mock_session_manager.update_cycle_state.assert_awaited_with(
            "01", jules_session_id="jules-new-456", status="in_progress"
        )

        assert result["status"] == "failure"
