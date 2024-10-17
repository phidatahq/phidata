from datetime import datetime, timezone


def current_utc() -> datetime:
    return datetime.now(timezone.utc)


def current_utc_str(format: str = "%Y-%m-%dT%H:%M:%S.%fZ") -> str:
    return current_utc().strftime(format)
