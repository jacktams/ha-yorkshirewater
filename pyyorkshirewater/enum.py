"""Enums for pyyorkshirewater."""

from enum import Enum


class TimePeriod(Enum):
    """Time period granularity for consumption data."""

    DAILY = "1"
    MONTHLY = "2"
    YEARLY = "3"
