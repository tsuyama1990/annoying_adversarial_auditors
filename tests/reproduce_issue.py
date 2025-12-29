import asyncio
import os
from unittest.mock import MagicMock
# Adjust import path if necessary based on actual structure, assuming dev_src is in path or installed
import sys
sys.path.append(os.path.abspath("dev_src"))

from ac_cdd_core.services.aider_client import AiderClient

# --- Mock Sandbox Runner ---
class MockSandboxRunner:
    def __init__(self):
        self.last_env = {}
        self.mock_exit_code = 0
        self.mock_stdout = "Audit passed."
        self.mock_stderr = ""

    async def run_command(self, cmd, check=False, env=None):
        self.last_env = env or {}
        return self.mock_stdout, self.mock_stderr, self.mock_exit_code

    async def sync_from_sandbox(self):
        pass

# --- Tests ---
async def test_env_passthrough():
    print("--- Test 1: Env Var Pass-Through ---")
    # Simulate host environment
    os.environ["OPENROUTER_API_KEY"] = "sk-or-test-key"
    os.environ["GEMINI_API_KEY"] = "AIza-test-key"
    
    client = AiderClient()
    runner = MockSandboxRunner()
    
    # We need to mock the internal behavior if it depends on real files or complex setup
    # But for now we rely on the logic inside run_audit calling runner.run_command
    
    try:
        await client.run_audit(["file.py"], "instruction", runner=runner)
    except Exception as e:
        print(f"⚠️  Execution failed (expected if logic is complex): {e}")

    # Verify keys are passed blindly
    env = runner.last_env
    if env.get("OPENROUTER_API_KEY") == "sk-or-test-key" and \
       env.get("GEMINI_API_KEY") == "AIza-test-key":
        print("✅ PASS: All defined keys were passed to sandbox.")
    else:
        print(f"❌ FAIL: Keys missing/mismatch. Got: {env.keys()}")

async def test_system_error_handling():
    print("\n--- Test 2: System Error Handling ---")
    client = AiderClient()
    runner = MockSandboxRunner()
    
    # Simulate Aider Crash
    runner.mock_exit_code = 1
    runner.mock_stderr = "Traceback: Authorization failed..."
    runner.mock_stdout = "Garbage output"
    
    try:
        result = await client.run_audit(["file.py"], "instruction", runner=runner)
        
        # Verify specific error prefix
        if result.startswith("SYSTEM_ERROR"):
            print("✅ PASS: Client caught crash and returned SYSTEM_ERROR.")
        else:
            print(f"❌ FAIL: Client returned raw output: {result[:50]}...")
    except Exception as e:
         print(f"⚠️  Execution failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_env_passthrough())
    asyncio.run(test_system_error_handling())
