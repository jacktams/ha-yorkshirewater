"""Example usage of pyyorkshirewater."""

import asyncio
import json
import os

import aiohttp

from custom_components.yorkshire_water.pyyorkshirewater import YorkshireWater
from custom_components.yorkshire_water.pyyorkshirewater.auth import YorkshireWaterAuth


async def main():
    username = os.environ.get("YW_EMAIL")
    password = os.environ.get("YW_PASSWORD")
    account_ref = os.environ.get("YW_ACCOUNT_REF", "519516290000000")

    if not username or not password:
        print("Set YW_EMAIL and YW_PASSWORD environment variables")
        return

    async with aiohttp.ClientSession(
        cookie_jar=aiohttp.CookieJar()
    ) as session:
        auth = YorkshireWaterAuth(
            username=username,
            password=password,
            session=session,
        )
        await auth.login()
        print(f"Authenticated as {username}")
        print(f"Token expires at {auth.token_expires_at}")

        yw = YorkshireWater(auth)
        result = await yw.update(account_reference=account_ref)

        print(f"\nTotal litres: {result['totalLitres']}")
        print(f"Total cost: \u00a3{result['totalCost']:.2f}")
        print(f"Daily average: {result['dailyLitresAverage']:.0f}L")
        print()

        for meter in yw.meters.values():
            print(f"Meter: {meter.serial_number}")
            print(f"  Latest consumption: {meter.latest_consumption}L")
            print(f"  Latest cost: \u00a3{meter.latest_cost:.2f}")
            print(f"  Yesterday consumption: {meter.yesterday_consumption}")
            print(f"  Last updated: {meter.last_updated}")
            print()
            print("Daily breakdown:")
            for r in meter.readings:
                print(
                    f"  {r['date']}: {r['totalConsumptionLitres']}L "
                    f"(\u00a3{r['totalCostIncludingSewerage']:.2f})"
                )


if __name__ == "__main__":
    asyncio.run(main())
