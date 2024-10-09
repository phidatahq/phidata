from datetime import datetime, timezone


def current_utc() -> datetime:
    return datetime.now(timezone.utc)


def current_utc_str() -> str:
    return current_utc().strftime("%Y-%m-%dT%H:%M:%S")
