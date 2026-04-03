# pyyorkshirewater

A Python package to interact with Yorkshire Water smart meters.

## Installation

```bash
pip install pyyorkshirewater
```

## Usage

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
