"""Shared helpers for parsing Jira API responses."""

from datetime import datetime


def parse_jira_datetime(dt_str: str) -> datetime:
    """Parse Jira datetime format to a Python datetime object."""
    if dt_str[-5] in ("+", "-") and dt_str[-3] != ":":
        dt_str = dt_str[:-2] + ":" + dt_str[-2:]
    return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
