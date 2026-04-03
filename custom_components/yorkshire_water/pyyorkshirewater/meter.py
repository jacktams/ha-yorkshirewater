"""Smart meter data model."""

from datetime import date, datetime, timedelta, timezone


class SmartMeter:
    """Represents a Yorkshire Water smart meter."""

    def __init__(self, serial_number: str):
        self.serial_number = serial_number
        self.readings: list[dict] = []

    def update_reading_cache(self, daily_usage_data: list[dict]) -> None:
        """Update the reading cache with new daily usage data."""
        existing_dates = {r["date"] for r in self.readings}
        for entry in daily_usage_data:
            if entry["date"] not in existing_dates:
                self.readings.append(entry)
        self.readings.sort(key=lambda r: r["date"])

    @property
    def latest_consumption(self) -> float | None:
        """Return the most recent day's consumption in litres."""
        if not self.readings:
            return None
        return float(self.readings[-1]["totalConsumptionLitres"])

    @property
    def latest_cost(self) -> float | None:
        """Return the most recent day's total cost."""
        if not self.readings:
            return None
        return self.readings[-1].get("totalCostIncludingSewerage")

    @property
    def yesterday_readings(self) -> list[dict]:
        """Return readings from yesterday."""
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        return [r for r in self.readings if r["date"] == yesterday]

    @property
    def yesterday_consumption(self) -> float | None:
        """Return yesterday's total consumption in litres."""
        readings = self.yesterday_readings
        if not readings:
            return None
        return sum(float(r["totalConsumptionLitres"]) for r in readings)

    @property
    def yesterday_cost(self) -> float | None:
        """Return yesterday's total cost."""
        readings = self.yesterday_readings
        if not readings:
            return None
        return sum(r.get("totalCostIncludingSewerage", 0) for r in readings)

    @property
    def last_updated(self) -> datetime | None:
        """Return the date of the most recent reading."""
        if not self.readings:
            return None
        dt = datetime.fromisoformat(self.readings[-1]["date"])
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt

    def to_dict(self) -> dict:
        """Serialize to dict."""
        return {
            "serial_number": self.serial_number,
            "latest_consumption": self.latest_consumption,
            "latest_cost": self.latest_cost,
            "yesterday_consumption": self.yesterday_consumption,
            "yesterday_cost": self.yesterday_cost,
            "last_updated": str(self.last_updated) if self.last_updated else None,
            "readings": self.readings,
        }
