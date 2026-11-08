"""Check the Anthropic key in .env without printing it. Uses a free model lookup, no tokens billed.

Usage:  .venv\\Scripts\\python check_key.py
"""
import anthropic
from dotenv import dotenv_values

import config

key = dotenv_values(config.ROOT / ".env").get("ANTHROPIC_API_KEY") or ""
print("Key present:", bool(key))
print("Starts with sk-ant-:", key.startswith("sk-ant-"))
print("Length:", len(key))
print("Contains spaces or quotes:", any(c in key for c in " \t\"'"))

if key:
    try:
        model = anthropic.Anthropic(api_key=key).models.retrieve(config.LLM_MODEL)
        print("Result: key works; model available:", model.id)
    except anthropic.AuthenticationError:
        print("Result: key rejected (authentication failed)")
    except anthropic.PermissionDeniedError:
        print("Result: key valid but lacks permission")
    except anthropic.NotFoundError:
        print("Result: key valid but model not available to this account")
    except anthropic.APIConnectionError:
        print("Result: network error")
