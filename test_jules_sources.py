import os
import json
import urllib.request
import urllib.error
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("JULES_API_KEY")

if not api_key:
    # Try looking in .env manually if load_dotenv failed or env not set
    try:
        with open(".env") as f:
            for line in f:
                if line.startswith("JULES_API_KEY="):
                    api_key = line.split("=", 1)[1].strip().strip('"')
                    break
    except:
        pass

if not api_key:
    print("FATAL: JULES_API_KEY not found in environment or .env")
    exit(1)

url = "https://jules.googleapis.com/v1alpha/sources"
headers = {"x-goog-api-key": api_key}

print(f"Testing connectivity to {url}...")
req = urllib.request.Request(url, headers=headers)

try:
    with urllib.request.urlopen(req) as response:
        print(f"Status: {response.status}")
        body = response.read().decode('utf-8')
        print(f"Response: {body}")
except urllib.error.HTTPError as e:
    print(f"HTTP Error: {e.code} {e.reason}")
    print(e.read().decode('utf-8'))
except Exception as e:
    print(f"Error: {e}")
