#!/usr/bin/env python3
"""Upload or update triage and implement playbooks to the Devin API.

Idempotent — safe to run multiple times. Creates new playbooks if they don't exist,
updates existing ones if the content has changed.

Usage:
    DEVIN_API_KEY=... python scripts/setup_playbooks.py
"""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path so we can import orchestrator
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from orchestrator.devin_client import DevinClient

PLAYBOOKS_DIR = Path(__file__).resolve().parent.parent / "playbooks"

PLAYBOOK_FILES = {
    "finserv-triage": PLAYBOOKS_DIR / "triage.md",
    "finserv-implement": PLAYBOOKS_DIR / "implement.md",
}


async def main() -> None:
    api_key = os.environ.get("DEVIN_API_KEY", "")
    org_id = os.environ.get("DEVIN_ORG_ID", "")

    if not api_key or not org_id:
        print("ERROR: DEVIN_API_KEY and DEVIN_ORG_ID environment variables are required.")
        sys.exit(1)

    client = DevinClient(api_key=api_key, org_id=org_id)

    # Fetch existing playbooks
    existing = await client.list_playbooks()
    existing_map = {p.title: p for p in existing}

    for title, filepath in PLAYBOOK_FILES.items():
        body = filepath.read_text()

        if title in existing_map:
            existing_pb = existing_map[title]
            if existing_pb.body.strip() == body.strip():
                print(f"  SKIP (unchanged): {title} -> {existing_pb.playbook_id}")
            else:
                await client.update_playbook(existing_pb.playbook_id, title, body)
                print(f"  UPDATED: {title} -> {existing_pb.playbook_id}")
        else:
            playbook_id = await client.create_playbook(title, body)
            print(f"  CREATED: {title} -> {playbook_id}")

    print("\nDone. Set these playbook IDs in your .env:")
    # Re-fetch to get final IDs
    final = await client.list_playbooks()
    for p in final:
        if p.title in PLAYBOOK_FILES:
            env_key = "TRIAGE_PLAYBOOK_ID" if "triage" in p.title else "IMPLEMENT_PLAYBOOK_ID"
            print(f"  {env_key}={p.playbook_id}")


if __name__ == "__main__":
    asyncio.run(main())
