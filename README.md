# Yorkshire Water for Home Assistant

A custom [Home Assistant](https://www.home-assistant.io/) integration for [Yorkshire Water](https://www.yorkshirewater.com/) smart meters, installable via [HACS](https://hacs.xyz/).

## Features

- Daily water consumption (litres)
- Daily water and sewerage costs
- Historical statistics in the HA energy dashboard
- Handles delayed meter readings (fetches a 7-day window)

## Installation (HACS)

1. Open HACS in Home Assistant
2. Go to Integrations > Custom Repositories
3. Add `https://github.com/jacktams/ha-yorkshirewater` as an Integration
4. Install "Yorkshire Water"
5. Restart Home Assistant
6. Go to Settings > Integrations > Add Integration > Yorkshire Water
7. Enter your Yorkshire Water email, password, and account reference number

## Sensors

| Sensor | Description | Unit |
|--------|-------------|------|
| Latest daily usage | Most recent available daily consumption | L |
| Latest daily cost | Most recent available daily cost | GBP |
| Yesterday's usage | Yesterday's consumption (None if delayed) | L |
| Yesterday's cost | Yesterday's cost (None if delayed) | GBP |
| Last reading date | Timestamp of the most recent reading | - |

## Python Library

This repo also includes `pyyorkshirewater`, a standalone async Python library for the Yorkshire Water API.

```python
import asyncio
import aiohttp
from pyyorkshirewater import YorkshireWater
from pyyorkshirewater.auth import YorkshireWaterAuth

async def main():
    async with aiohttp.ClientSession() as session:
        auth = YorkshireWaterAuth(
            username="your@email.com",
            password="your_password",
            session=session,
        )
        await auth.login()

        yw = YorkshireWater(auth)
        await yw.update(account_reference="your_account_reference")

        for meter in yw.meters.values():
            print(f"Meter: {meter.serial_number}")
            print(f"Latest consumption: {meter.latest_consumption}L")
            print(f"Yesterday cost: {meter.yesterday_cost}")

asyncio.run(main())
```
