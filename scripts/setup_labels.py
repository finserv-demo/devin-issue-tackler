#!/usr/bin/env python3
"""Create all devin:* labels on the target GitHub repository.

Idempotent — safe to run multiple times. Skips labels that already exist.

Usage:
    GITHUB_TOKEN=... TARGET_REPO=finserv-demo/finserv python scripts/setup_labels.py
"""

import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path so we can import orchestrator
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from orchestrator.github_client import GitHubClient
from orchestrator.labels import LABEL_DEFINITIONS


async def main() -> None:
    token = os.environ.get("GITHUB_TOKEN", "")
    repo = os.environ.get("TARGET_REPO", "finserv-demo/finserv")

    if not token:
        print("ERROR: GITHUB_TOKEN environment variable is required.")
        sys.exit(1)

    client = GitHubClient(token=token, repo=repo)

    print(f"Setting up {len(LABEL_DEFINITIONS)} labels on {repo}...")
    await client.ensure_labels_exist(LABEL_DEFINITIONS)
    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
