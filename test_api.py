from dotenv import load_dotenv
load_dotenv()

import os
import anthropic

api_key = os.environ.get("ANTHROPIC_API_KEY")
print(f"API key found: {'yes' if api_key else 'NO'}")
if api_key:
    print(f"Key prefix: {api_key[:8]}...")

try:
    client = anthropic.Anthropic(api_key=api_key)
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=64,
        messages=[{"role": "user", "content": "hi"}],
    )
    print("SUCCESS")
    print(response)
except Exception as e:
    print(f"ERROR: {type(e).__name__}: {e}")
