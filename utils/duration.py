import re


DURATION_PATTERN = re.compile(
    r"^(?:(\d+)d)?(?:(\d+)h)?(?:(\d+)m)?(?:(\d+)s)?$",
    re.IGNORECASE
)


def parse_duration(duration: str) -> int | None:
    match = DURATION_PATTERN.fullmatch(duration.strip())

    if not match:
        return None

    days = int(match.group(1) or 0)
    hours = int(match.group(2) or 0)
    minutes = int(match.group(3) or 0)
    seconds = int(match.group(4) or 0)

    total_seconds = (
        days * 86400
        + hours * 3600
        + minutes * 60
        + seconds
    )

    if total_seconds <= 0:
        return None

    return total_seconds