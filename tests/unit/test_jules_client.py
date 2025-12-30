import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from ac_cdd_core.services.jules_client import JulesClient, JulesSessionError, JulesTimeoutError


@pytest.mark.asyncio
async def test_jules_url_construction():
    """Test URL construction for Jules API."""
    client = JulesClient()
    # Mock base attributes
    client.base_url = "https://api.example.com"
    client._get_headers = MagicMock(return_value={})

    # Test _send_message
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value.status_code = 200

        # Relative path
        await client._send_message("sessions/123", "hello")
        url = mock_post.call_args[0][0]
        assert url == "https://api.example.com/sessions/123:sendMessage"

        # Absolute path (should not double prepend)
        await client._send_message("https://api.example.com/sessions/456", "hello")
        url = mock_post.call_args[0][0]
        assert url == "https://api.example.com/sessions/456:sendMessage"


def test_list_activities_delegation():
    """Test delegation to API client."""
    client = JulesClient()
    client.api_client = MagicMock()

    client.list_activities("sessions/123")
    client.api_client.list_activities.assert_called_once_with("sessions/123")


@pytest.mark.asyncio
async def test_run_session_success(tmp_path):
    """Test successful session execution."""
    client = JulesClient()
    client.git = AsyncMock()
    client.git.get_remote_url.return_value = "https://github.com/user/repo.git"
    client.git.get_current_branch.return_value = "main"

    completion_file = tmp_path / "test_completion"
    
    with (
        patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post,
        patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get,
        patch.object(client, "_check_for_inquiry", return_value=None),
    ):
        # Mock create session response
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"name": "sessions/123"}
        
        # Mock poll response (SUCCEEDED with PR)
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "state": "SUCCEEDED",
            "outputs": [
                {"pullRequest": {"url": "https://github.com/pr/1"}}
            ]
        }
        
        pr_url = await client.run_session(
            session_id="test",
            prompt="do it",
            files=[],
            completion_signal_file=completion_file
        )
        
        assert pr_url["pr_url"] == "https://github.com/pr/1"


@pytest.mark.asyncio
async def test_run_session_timeout(tmp_path):
    """Test timeout during session."""
    client = JulesClient()
    client.timeout = 0.1  # Fast timeout
    client.poll_interval = 0.1
    client.git = AsyncMock()
    client.git.get_remote_url.return_value = "https://github.com/user/repo"

    completion_file = tmp_path / "test_completion"
    
    with (
        patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post,
        patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get,
    ):
        # Create session ok
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {"name": "sessions/123"}
        
        # Poll keeps returning RUNNING
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"state": "RUNNING"}
        
        with pytest.raises(JulesTimeoutError):
            await client.run_session("test", "prompt", [], completion_file)


@pytest.mark.asyncio
async def test_continue_session(tmp_path):
    """Test continue session flow."""
    client = JulesClient()
    
    with (
        patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post,
        patch.object(client, "wait_for_completion") as mock_wait,
    ):
        mock_post.return_value.status_code = 200
        mock_wait.return_value = {"pr_url": "https://pr", "status": "success"}
        
        result = await client.continue_session("sessions/123", "feedback")
        
        assert result["pr_url"] == "https://pr"
        mock_post.assert_called() # sendMessage called
        mock_wait.assert_called()


@pytest.mark.asyncio
async def test_wait_for_completion_pr_created(tmp_path):
    """Test polling loop finds PR."""
    client = JulesClient()
    client.poll_interval = 0.01
    
    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        # First call running, second succeeded
        mock_get.side_effect = [
            MagicMock(status_code=200, json=lambda: {"state": "RUNNING"}),
            MagicMock(status_code=200, json=lambda: {
                "state": "SUCCEEDED",
                "outputs": [{"pullRequest": {"url": "https://pr"}}]
            }),
        ]
        
        result = await client.wait_for_completion("sessions/123")
        assert result["pr_url"] == "https://pr"


@pytest.mark.asyncio
async def test_check_for_inquiry_found():
    """Test detecting user inquiry in activities."""
    client = JulesClient()
    
    mock_client = AsyncMock()
    
    # Mock activities response with inquiry
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "activities": [
            {
                "id": "act123",
                "type": "USER_FEEDBACK_REQUESTED",
                "message": "What should I do?"
            }
        ]
    }
    mock_client.get.return_value = mock_response
    
    result = await client._check_for_inquiry(mock_client, "sessions/123")
    
    assert result is not None
    assert result[0] == "What should I do?"


@pytest.mark.asyncio
async def test_check_for_inquiry_not_found():
    """Test detecting no inquiry."""
    client = JulesClient()
    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.json.return_value = {"activities": []}
    mock_client.get.return_value = mock_response
    
    result = await client._check_for_inquiry(mock_client, "sessions/123")
    assert result is None


@pytest.mark.asyncio
async def test_send_message_success():
    """Test sending message to session."""
    client = JulesClient()
    client.base_url = "https://api.example.com"
    client._get_headers = MagicMock(return_value={"Authorization": "Bearer token"})
    
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value.status_code = 200
        
        await client._send_message("sessions/123", "Hello")
        
        # Verify URL and payload
        args, kwargs = mock_post.call_args
        assert args[0] == "https://api.example.com/sessions/123:sendMessage"
        assert kwargs["json"] == {"prompt": "Hello"}
