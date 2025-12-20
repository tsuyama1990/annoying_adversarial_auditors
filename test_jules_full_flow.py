import os
import json
import time
import urllib.request
import urllib.error
from typing import Any, Dict, List

# --- Standalone Client Implementation (copied logic to ensure isolation) ---

class SimpleJulesClient:
    BASE_URL = "https://jules.googleapis.com/v1alpha"

    def __init__(self):
        # 1. Load API Key
        self.api_key = os.getenv("JULES_API_KEY")
        if not self.api_key:
            # Try .env
            try:
                with open(".env") as f:
                    for line in f:
                        if line.startswith("JULES_API_KEY="):
                            self.api_key = line.split("=", 1)[1].strip().strip('"')
                            break
            except:
                pass
        
        if not self.api_key:
            raise ValueError("JULES_API_KEY not found. Please set it in .env")
            
        self.headers = {
            "x-goog-api-key": self.api_key,
            "Content-Type": "application/json"
        }
        print(f"API Key loaded (len={len(self.api_key)})")

    def _request(self, method: str, endpoint: str, data: Dict = None) -> Dict:
        url = f"{self.BASE_URL}/{endpoint}"
        body = json.dumps(data).encode("utf-8") if data else None
        
        req = urllib.request.Request(url, method=method, headers=self.headers, data=body)
        
        try:
            with urllib.request.urlopen(req) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            print(f"HTTP Error {e.code}: {e.read().decode('utf-8')}")
            raise

    def list_sources(self) -> List[Dict]:
        print("Listing sources...")
        data = self._request("GET", "sources")
        return data.get("sources", [])

    def create_session(self, source: str) -> Dict:
        print(f"Creating session for source: {source}...")
        payload = {
            "prompt": "Hello Jules! Please reply with 'Session Active' to confirm you are listening.",
            "sourceContext": {
                "source": source,
                "githubRepoContext": {
                    "startingBranch": "main"
                }
            }
        }
        return self._request("POST", "sessions", payload)

    def list_activities(self, session_name: str) -> List[Dict]:
        try:
            return self._request("GET", f"{session_name}/activities").get("activities", [])
        except urllib.error.HTTPError as e:
            if e.code == 404:
                print("(404 on listing activities, retrying...)")
                return []
            raise

# --- Main Test Execution ---

def main():
    try:
        client = SimpleJulesClient()
        
        # 1. Get Source
        sources = client.list_sources()
        if not sources:
            print("No sources found!")
            return

        # Pick one (prefer the current repo if possible)
        selected_source = sources[0]["name"]
        for s in sources:
            print(f"Found source: {s['name']}")
            if "template_cli_agent" in s['name']:
                selected_source = s['name']
        
        print(f"Selected source: {selected_source}")

        # 2. Create Session
        session = client.create_session(selected_source)
        session_name = session["name"]
        print(f"SUCCESS! Session Created. Name: {session_name}")
        print(f"Link (if applicable): https://jules.google/sessions/{session_name.split('/')[-1]}")

        # 3. Poll for response
        print("Polling for activities (wait 30s)...")
        seen_activities = set()
        
        for i in range(6): # Poll for 30 seconds
            activities = client.list_activities(session_name)
            for act in activities:
                name = act['name']
                if name not in seen_activities:
                    print(f"\n[NEW ACTIVITY] {name}")
                    # Try to print content
                    if 'message' in act:
                        print(f"Message: {act['message']}")
                    if 'text' in act:
                        print(f"Text: {act['text']}")
                    seen_activities.add(name)
            
            time.sleep(5)
            print(".", end="", flush=True)
            
        print("\nTest Complete.")

    except Exception as e:
        print(f"\nFATAL ERROR: {e}")

if __name__ == "__main__":
    main()
