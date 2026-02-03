import aiohttp
import datetime
import asyncio
import os
from aiohttp import TCPConnector
from dotenv import load_dotenv

load_dotenv()

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")

async def main ():
    url = "https://navitime-transport.p.rapidapi.com/transport_node"
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": "navitime-transport.p.rapidapi.com",
    }


    connector = TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        async def _get_id(station):
            res = await session.get(url, headers=headers, params={"word": station})
            data = await res.json()
            return data #["items"][0]["id"]
        

if __name__ == "__main__":
    asyncio.run(main())