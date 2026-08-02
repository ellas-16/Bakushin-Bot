import json
from pathlib import Path

BACKUP_FILE = Path("data/role_backups.json")



def load_backups() -> dict:
    if not BACKUP_FILE.exists():
        return {}

    try:
        return json.loads(BACKUP_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def save_backups(backups: dict) -> None:
    BACKUP_FILE.write_text(json.dumps(backups, indent=2), encoding="utf-8")
