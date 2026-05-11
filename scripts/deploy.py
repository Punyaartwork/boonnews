#!/usr/bin/env python3
"""Deploy boonnews to VPS via git pull over SSH.

Usage:
    python scripts/deploy.py [--host HOST] [--user USER] [--path PATH] [--port PORT]

Config resolution order (first wins):
    1. CLI arguments
    2. Environment variables
    3. .env file at repo root

Required:
    BOONNEWS_VPS_HOST   VPS hostname or IP
    BOONNEWS_VPS_USER   SSH username
    BOONNEWS_VPS_PATH   Remote repo path (e.g. /var/www/boonnews)

Optional:
    BOONNEWS_VPS_PORT   SSH port (default 22)
    BOONNEWS_VPS_URL    Site URL printed on success
    BOONNEWS_VPS_BRANCH Git branch to pull (default main)

Assumes SSH key auth — `BatchMode=yes` prevents password prompts.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = ROOT / ".env"


def load_env_file() -> dict:
    env = {}
    if not ENV_FILE.exists():
        return env
    for raw in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def resolve(arg_val, env_key: str, file_env: dict, default=None):
    if arg_val is not None and arg_val != "":
        return arg_val
    if os.environ.get(env_key):
        return os.environ[env_key]
    if file_env.get(env_key):
        return file_env[env_key]
    return default


def main() -> int:
    parser = argparse.ArgumentParser(description="Deploy boonnews to VPS")
    parser.add_argument("--host", help="VPS hostname or IP")
    parser.add_argument("--user", help="SSH username")
    parser.add_argument("--path", help="Remote repo path (e.g. /var/www/boonnews)")
    parser.add_argument("--port", type=int, help="SSH port (default 22)")
    parser.add_argument("--branch", help="Git branch to pull (default main)")
    parser.add_argument("--url", help="Site URL printed on success")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the SSH command without executing",
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Fail fast on auth prompts (set BOONNEWS_VPS_BATCH=true to default-on)",
    )
    args = parser.parse_args()

    file_env = load_env_file()

    host = resolve(args.host, "BOONNEWS_VPS_HOST", file_env)
    user = resolve(args.user, "BOONNEWS_VPS_USER", file_env)
    path = resolve(args.path, "BOONNEWS_VPS_PATH", file_env)
    port = int(resolve(args.port, "BOONNEWS_VPS_PORT", file_env, default=22))
    branch = resolve(args.branch, "BOONNEWS_VPS_BRANCH", file_env, default="main")
    url = resolve(args.url, "BOONNEWS_VPS_URL", file_env)

    missing = [
        n for n, v in [
            ("BOONNEWS_VPS_HOST", host),
            ("BOONNEWS_VPS_USER", user),
            ("BOONNEWS_VPS_PATH", path),
        ] if not v
    ]
    if missing:
        print(f"ERROR: missing config: {missing}", file=sys.stderr)
        print(
            "Set via env, .env file in repo root, or CLI args (--host, --user, --path).",
            file=sys.stderr,
        )
        return 2

    # Quote remote path to handle spaces; use git -C for clarity.
    remote_cmd = (
        f"set -e; "
        f"cd {shell_quote(path)} && "
        f"git fetch origin {shell_quote(branch)} && "
        f"git reset --hard origin/{shell_quote(branch)} && "
        f"echo '--- HEAD ---' && git log -1 --oneline"
    )

    batch_mode = args.batch or (
        os.environ.get("BOONNEWS_VPS_BATCH", file_env.get("BOONNEWS_VPS_BATCH", "")).lower()
        in ("1", "true", "yes")
    )

    ssh_cmd = ["ssh", "-p", str(port), "-o", "StrictHostKeyChecking=accept-new"]
    if batch_mode:
        ssh_cmd += ["-o", "BatchMode=yes"]
    ssh_cmd += [f"{user}@{host}", remote_cmd]

    print(f"→ Deploying to {user}@{host}:{path} (branch: {branch})")
    print(f"  $ ssh -p {port} {user}@{host} '<remote_cmd>'")
    if args.dry_run:
        print("\nDRY RUN — remote command:")
        print(f"  {remote_cmd}")
        return 0

    print()
    result = subprocess.run(ssh_cmd)
    if result.returncode != 0:
        print(f"\n✗ Deploy failed (exit {result.returncode})", file=sys.stderr)
        print(
            "Check: (1) SSH key configured, (2) remote path exists, "
            "(3) remote is a git repo, (4) host reachable.",
            file=sys.stderr,
        )
        return 3

    print()
    print("✓ Deploy successful")
    if url:
        print(f"  → {url}")
    return 0


def shell_quote(s: str) -> str:
    """Quote a string for use in a remote shell command."""
    return "'" + s.replace("'", "'\\''") + "'"


if __name__ == "__main__":
    sys.exit(main())
