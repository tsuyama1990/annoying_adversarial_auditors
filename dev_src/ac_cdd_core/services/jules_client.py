import asyncio
import json
import httpx
from typing import Any, Optional, Dict
from pathlib import Path

from ac_cdd_core.config import settings
from ac_cdd_core.utils import logger
from ac_cdd_core.services.git_ops import GitManager
from rich.console import Console

console = Console()

class JulesSessionError(Exception):
    pass

class JulesTimeoutError(JulesSessionError):
    pass

class JulesClient:
    """
    Client for interacting with the Google Cloud Code Agents API (Jules API).
    Uses asynchronous HTTP requests to submit tasks and poll for Pull Request creation.
    """

    def __init__(self) -> None:
        self.api_key = settings.JULES_API_KEY
        self.project_id = settings.GCP_PROJECT_ID
        self.region = settings.GCP_REGION
        # The base URL is constructed based on project and location
        # Endpoint: POST https://jules.googleapis.com/v1alpha/projects/{project}/locations/{location}/sessions
        self.base_url = "https://jules.googleapis.com/v1alpha"
        self.timeout = settings.jules.timeout_seconds
        self.poll_interval = settings.jules.polling_interval_seconds
        self.console = Console()
        self.git = GitManager()

        if not self.api_key:
            logger.warning("JULES_API_KEY is not set. JulesClient will fail if called.")
        if not self.project_id:
            logger.warning("GCP_PROJECT_ID is not set. JulesClient will fail if called.")

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key or "",
        }

    async def run_session(
        self,
        session_id: str,
        prompt: str,
        files: list[str],
        completion_signal_file: Path, # Kept for signature compatibility but unused logic-wise
        runner: Any = None, # Deprecated/Unused in API mode (Jules runs in its own cloud)
    ) -> Dict[str, Any]:
        """
        Orchestrates the Jules session:
        1. Creates a session with 'AUTO_CREATE_PR' mode.
        2. Polls for completion.
        3. Returns the PR URL.
        """
        if not self.api_key or not self.project_id:
            raise JulesSessionError("Missing JULES_API_KEY or GCP_PROJECT_ID configuration.")

        # 1. Prepare Source Context
        # We need to know the repo owner/name and the current branch.
        # We assume the local git is the source of truth for "where we are".
        try:
            repo_url = await self.git.get_remote_url()
            # Parse owner/repo from URL (e.g., https://github.com/owner/repo.git or git@github.com:owner/repo.git)
            # This is a basic parser.
            if "github.com" in repo_url:
                parts = repo_url.replace(".git", "").split("/")
                repo_name = parts[-1]
                owner = parts[-2].split(":")[-1] # Handle git@github.com:owner
            else:
                # Fallback or error
                raise JulesSessionError(f"Unsupported repository URL format: {repo_url}. Only GitHub is supported.")

            branch = await self.git.get_current_branch()
        except Exception as e:
            raise JulesSessionError(f"Failed to determine git context: {e}") from e

        # 2. Create Session
        logger.info(f"Creating Jules Session {session_id} on branch {branch}...")

        # Construct the specific API endpoint
        url = f"{self.base_url}/projects/{self.project_id}/locations/{self.region}/sessions"

        # Payload construction
        # Note: The prompt is passed as the initial user message.
        # Files are not uploaded directly; Jules accesses the repo via sourceContext.
        # However, we might need to specify which files to look at in the prompt.

        # Add file list to prompt if provided, to give context
        full_prompt = prompt
        if files:
            file_list_str = "\n".join(files)
            full_prompt += f"\n\nPlease focus on the following files:\n{file_list_str}"

        payload = {
            "automationMode": "AUTO_CREATE_PR",
            "sourceContext": {
                "gitHubRepository": {
                    "owner": owner,
                    "repo": repo_name
                },
                "branchName": branch
            },
            "userMessage": {
                "content": full_prompt
            }
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, json=payload, headers=self._get_headers(), timeout=30.0)
                if response.status_code != 200:
                    # Try to parse error
                    error_msg = response.text
                    try:
                        err_json = response.json()
                        error_msg = err_json.get("error", {}).get("message", response.text)
                    except:
                        pass
                    raise JulesSessionError(f"Failed to create session: {response.status_code} - {error_msg}")

                resp_data = response.json()
                # The response should contain the session name/ID to poll
                # Format: projects/{p}/locations/{l}/sessions/{uuid}
                session_name = resp_data.get("name")
                if not session_name:
                    raise JulesSessionError("API did not return a session name.")

            except httpx.RequestError as e:
                raise JulesSessionError(f"Network error creating session: {e}") from e

        # 3. Poll for Completion
        logger.info(f"Session created: {session_name}. Waiting for PR creation...")
        return await self.wait_for_completion(session_name)

    async def wait_for_completion(self, session_name: str) -> Dict[str, Any]:
        """
        Polls the session until it succeeds or fails.
        Returns a dict containing the PR URL.
        """
        url = f"{self.base_url}/{session_name}"

        start_time = asyncio.get_event_loop().time()

        status_context = self.console.status("[bold green]Jules is working on your PR...", spinner="dots")
        status_context.start()

        async with httpx.AsyncClient() as client:
            try:
                while True:
                    if asyncio.get_event_loop().time() - start_time > self.timeout:
                        raise JulesTimeoutError("Timed out waiting for Jules to complete.")

                    try:
                        response = await client.get(url, headers=self._get_headers(), timeout=10.0)
                        if response.status_code != 200:
                            logger.warning(f"Polling error: {response.status_code} - {response.text}")
                            # Don't crash on transient polling errors
                            await asyncio.sleep(self.poll_interval)
                            continue

                        data = response.json()
                        state = data.get("state") # e.g., STATE_UNSPECIFIED, ACTIVE, SUCCEEDED, FAILED

                        # Check for Pull Request
                        # The API should return the PR link in the response, possibly under 'pullRequest'
                        # or similar field depending on exact API spec.
                        # Based on prompt: "Status SUCCEEDED or pullRequest field exists"

                        pr_info = data.get("pullRequest")
                        if pr_info and pr_info.get("htmlUrl"):
                            status_context.stop()
                            pr_url = pr_info.get("htmlUrl")
                            logger.info(f"Jules Task Completed. PR Created: {pr_url}")
                            # We return a dict that resembles what the caller might expect loosely,
                            # but primarily communicating the PR URL.
                            # The caller (graph.py) currently expects parsed JSON from a file.
                            # We will need to adapt the caller.
                            return {"pr_url": pr_url, "status": "success", "raw": data}

                        if state == "SUCCEEDED":
                            # If SUCCEEDED but no PR info found yet (maybe in a different field?), return what we have.
                            status_context.stop()
                            logger.info("Jules Session Succeeded.")
                            return {"status": "success", "raw": data}

                        if state == "FAILED":
                            status_context.stop()
                            error_msg = data.get("error", {}).get("message", "Unknown error")
                            logger.error(f"Jules Session Failed: {error_msg}")
                            raise JulesSessionError(f"Jules Session Failed: {error_msg}")

                    except httpx.RequestError as e:
                        logger.warning(f"Network error polling: {e}")

                    await asyncio.sleep(self.poll_interval)

            finally:
                status_context.stop()
