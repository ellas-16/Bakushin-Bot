import json
from pathlib import Path

CASES_FILE = Path("data/cases.json")

def load_cases():
    if not CASES_FILE.exists():
        return []

    try:
        with open(CASES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []

def save_cases(cases):
    with open(CASES_FILE, "w", encoding="utf-8") as f:
        json.dump(cases, f, indent=4)

def get_next_case_id():
    cases = load_cases()

    if not cases:
        return 1

    return max(case["id"] for case in cases) + 1


from datetime import datetime


def create_case(
    guild_id: int,
    user_id: int,
    moderator_id: int,
    action: str,
    reason: str,
    duration: str | None = None,
):
    cases = load_cases()

    case = {
        "id": get_next_case_id(),
        "guild_id": guild_id,
        "user_id": user_id,
        "moderator_id": moderator_id,
        "action": action,
        "reason": reason,
        "duration": duration,
        "timestamp": datetime.utcnow().isoformat(),
    }

    cases.append(case)
    save_cases(cases)

    return case

def get_user_cases(guild_id: int, user_id: int):
    cases = load_cases()

    return [
        case
        for case in cases
        if case["guild_id"] == guild_id
        and case["user_id"] == user_id
    ]


def delete_case(guild_id: int, case_id: int) -> bool:
    cases = load_cases()

    for case in cases:
        if (
            case["guild_id"] == guild_id
            and case["id"] == case_id
            and case["action"].lower() == "warn"
        ):
            cases.remove(case)
            save_cases(cases)
            return True

    return False