import pytz
import datetime


def get_utc_timestamp(unix_timestamp: int) -> datetime.datetime:
    """Get the UTC datetime from unix timestamp"""
    return datetime.datetime.fromtimestamp(unix_timestamp, pytz.utc)
