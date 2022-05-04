import datetime as dt
from typing import Optional


def dttm_str_to_dttm(
    dttm_str: str, dttm_format: str = "%Y-%m-%dT%H:%M:%S.%f"
) -> Optional[dt.datetime]:
    """Convert a datestamp string to a Date object"""

    try:
        datetime_object = dt.datetime.strptime(dttm_str, dttm_format)
        return datetime_object
    except Exception as e:
        pass
    return None


def dttm_to_dttm_str(dttm: dt.datetime, dttm_format: str = "%Y-%m-%dT%H:%M:%S") -> str:
    """Convert a datetime object to formatted string"""
    return dt.datetime.strftime(dttm, dttm_format)


def utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def days_ago(n=1, hour=0, minute=0, second=0, microsecond=0):
    """
    Get a datetime object representing `n` days ago.
    """
    today = utc_now().replace(
        hour=hour, minute=minute, second=second, microsecond=microsecond
    )
    return today - dt.timedelta(days=n)


def get_today_utc_date_str() -> str:
    today = utc_now().date()
    return today.strftime("%Y_%m_%d")


def utc_now_str() -> str:
    return dttm_to_dttm_str(utc_now())
