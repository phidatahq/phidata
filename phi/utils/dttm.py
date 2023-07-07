from datetime import datetime, timezone


def current_datetime_utc() -> datetime:
    return datetime.now(timezone.utc)
