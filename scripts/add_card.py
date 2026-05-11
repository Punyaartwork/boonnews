#!/usr/bin/env python3
"""Add a new event card to boonnews.

Usage:
    python scripts/add_card.py --json '<JSON>' --image inbox/card.jpg [--slug NAME] [--no-git] [--dry-run]
    python scripts/add_card.py --json '<JSON>' --image inbox/a.jpg inbox/b.jpg

Pipeline:
    1. Parse + validate JSON against schema
    2. Auto-assign id if missing (max + 1)
    3. Auto-fill date_display, important, contact if missing
    4. Move image(s) inbox/ -> cards/{date}_{slug}_{NN}.{ext}
    5. Append event to events.json
    6. git add . && git commit && git push origin main
    7. Roll back image moves and events.json on failure
"""

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVENTS_FILE = ROOT / "events.json"
CARDS_DIR = ROOT / "cards"
INBOX_DIR = ROOT / "inbox"

WHITELIST = {"งานบุญ", "ทำบุญ", "เทศกาล", "งานอบรม", "ต่างประเทศ", "ศูนย์สาขา"}
REQUIRED_FIELDS = {"temple", "title", "date", "categories"}
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

THAI_MONTHS = [
    "", "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
    "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"
]


class ValidationError(Exception):
    pass


def slugify(temple: str, override: str | None = None) -> str:
    """Generate a filesystem-safe slug for the temple.

    Priority: --slug override > ASCII chars in temple > md5 hash.
    """
    if override:
        cleaned = re.sub(r"[^a-zA-Z0-9_-]", "", override).lower()
        if cleaned:
            return cleaned[:24]
    ascii_only = re.sub(r"[^a-zA-Z0-9]", "", temple).lower()
    if len(ascii_only) >= 3:
        return ascii_only[:24]
    return "wat" + hashlib.md5(temple.encode("utf-8")).hexdigest()[:6]


def thai_date_display(date_str: str) -> str:
    """Convert 2026-05-22 -> 'วันที่ 22 พฤษภาคม 2569'."""
    y, m, d = (int(x) for x in date_str.split("-"))
    return f"วันที่ {d} {THAI_MONTHS[m]} {y + 543}"


def load_events() -> list:
    if not EVENTS_FILE.exists():
        return []
    text = EVENTS_FILE.read_text(encoding="utf-8")
    return json.loads(text) if text.strip() else []


def save_events(events: list) -> None:
    EVENTS_FILE.write_text(
        json.dumps(events, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def validate(event: dict) -> None:
    missing = REQUIRED_FIELDS - set(event.keys())
    if missing:
        raise ValidationError(f"Missing required fields: {sorted(missing)}")

    if not isinstance(event["temple"], str) or not event["temple"].strip():
        raise ValidationError("`temple` must be a non-empty string")
    if not isinstance(event["title"], str) or not event["title"].strip():
        raise ValidationError("`title` must be a non-empty string")

    if not isinstance(event["date"], str) or not DATE_RE.match(event["date"]):
        raise ValidationError(f"`date` must be YYYY-MM-DD, got: {event['date']!r}")
    try:
        datetime.strptime(event["date"], "%Y-%m-%d")
    except ValueError as exc:
        raise ValidationError(f"Invalid calendar date: {exc}")

    cats = event["categories"]
    if not isinstance(cats, list) or not cats:
        raise ValidationError("`categories` must be a non-empty list")
    invalid = [c for c in cats if c not in WHITELIST]
    if invalid:
        raise ValidationError(
            f"Invalid categories: {invalid}. "
            f"Whitelist: {sorted(WHITELIST)}"
        )

    if "important" in event and not isinstance(event["important"], bool):
        raise ValidationError("`important` must be a boolean")

    if "id" in event and not isinstance(event["id"], int):
        raise ValidationError("`id` must be an integer")


def run_git(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    print(f"  $ git {' '.join(args)}")
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    if check and result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} -> exit {result.returncode}")
    return result


def rollback_moves(moved: list[tuple[Path, Path]]) -> None:
    """Best-effort: move files from cards/ back to inbox/."""
    for src, target in moved:
        try:
            if target.exists() and not src.exists():
                shutil.move(str(target), str(src))
                print(f"  rolled back: cards/{target.name} -> {src.relative_to(ROOT)}")
        except Exception as exc:
            print(f"  WARN: rollback failed for {target.name}: {exc}", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Add a new event card to boonnews",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--json", required=True, help="Event JSON string")
    parser.add_argument(
        "--image",
        nargs="+",
        default=[],
        help="One or more image paths (relative to repo root or absolute)",
    )
    parser.add_argument("--slug", help="Optional override slug for filenames")
    parser.add_argument("--no-git", action="store_true", help="Skip git operations")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and print event JSON without writing anything",
    )
    args = parser.parse_args()

    # 1. Parse JSON
    try:
        event = json.loads(args.json)
    except json.JSONDecodeError as exc:
        print(f"ERROR: invalid JSON: {exc}", file=sys.stderr)
        return 2
    if not isinstance(event, dict):
        print("ERROR: JSON must be an object, not array/scalar", file=sys.stderr)
        return 2

    # 2. Validate
    try:
        validate(event)
    except ValidationError as exc:
        print(f"ERROR: validation failed: {exc}", file=sys.stderr)
        return 3

    # 3. Auto-fill
    events = load_events()
    existing_ids = {e["id"] for e in events}
    if "id" in event:
        if event["id"] in existing_ids:
            print(f"ERROR: id={event['id']} already exists", file=sys.stderr)
            return 4
    else:
        event["id"] = (max(existing_ids) + 1) if existing_ids else 1

    if "date_display" not in event:
        event["date_display"] = thai_date_display(event["date"])
    event.setdefault("important", False)
    event.setdefault("contact", "")

    # 4. Plan image moves
    slug = slugify(event["temple"], args.slug)
    planned: list[tuple[Path, Path]] = []
    for i, img in enumerate(args.image, start=1):
        src = Path(img)
        if not src.is_absolute():
            src = ROOT / src
        if not src.exists():
            print(f"ERROR: image not found: {src}", file=sys.stderr)
            return 5
        if not src.is_file():
            print(f"ERROR: not a file: {src}", file=sys.stderr)
            return 5
        ext = src.suffix.lower() or ".jpg"
        target_name = f"{event['date']}_{slug}_{i:02d}{ext}"
        target = CARDS_DIR / target_name
        if target.exists():
            print(f"ERROR: target already exists: cards/{target_name}", file=sys.stderr)
            return 6
        planned.append((src, target))

    event["cards"] = [t.name for _, t in planned]
    event["card_count"] = len(planned)

    # 5. Dry run exit
    if args.dry_run:
        print("DRY RUN — validation passed. Resolved event:")
        print(json.dumps(event, ensure_ascii=False, indent=2))
        if planned:
            print("\nPlanned image moves:")
            for src, tgt in planned:
                print(f"  {src.relative_to(ROOT)} -> cards/{tgt.name}")
        return 0

    # 6. Execute image moves
    CARDS_DIR.mkdir(parents=True, exist_ok=True)
    moved: list[tuple[Path, Path]] = []
    for src, target in planned:
        try:
            shutil.move(str(src), str(target))
            moved.append((src, target))
            print(f"  moved {src.relative_to(ROOT)} -> cards/{target.name}")
        except Exception as exc:
            print(f"ERROR moving {src}: {exc}", file=sys.stderr)
            rollback_moves(moved)
            return 7

    # 7. Update events.json
    events.append(event)
    try:
        save_events(events)
        print(f"  events.json updated ({len(events)} total)")
    except Exception as exc:
        print(f"ERROR saving events.json: {exc}", file=sys.stderr)
        rollback_moves(moved)
        return 8

    # 8. Git ops
    if not args.no_git:
        try:
            run_git("add", ".")
            commit_msg = f"add: {event['temple']} - {event['title']} ({event['date']})"
            run_git("commit", "-m", commit_msg)
            run_git("push", "origin", "main")
        except Exception as exc:
            print(f"ERROR during git: {exc}", file=sys.stderr)
            print(
                "NOTE: local files were saved. Commit may have been created locally.\n"
                "Investigate with `git status` / `git log -1` and resolve manually.",
                file=sys.stderr,
            )
            return 9

    print()
    print(f"✓ Added event id={event['id']}: {event['temple']} - {event['title']}")
    print(f"  date: {event['date']} ({event['date_display']})")
    print(f"  categories: {event['categories']}")
    print(f"  cards: {event['cards'] or '(none)'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
