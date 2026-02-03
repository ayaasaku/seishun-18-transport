import aiohttp
import datetime
import asyncio
import json
import os

from aiohttp import TCPConnector
from dotenv import load_dotenv

load_dotenv()

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")

def datetime_to_str(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%S")



def str_to_datetime(s):
    return datetime.datetime.strptime(s, "%Y-%m-%dT%H:%M:%S+09:00")


class StopOptionsLister:
    async def __init__(
        self, start, goal, start_time, max_travel_time=60 * 6, latest_stop_time=19
    ):
      
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
                return data["items"][0]["id"]

           
            self.start_station, self.goal_station = await asyncio.gather(
                _get_id(start),
                _get_id(goal)
            )

        
        self.session = aiohttp.ClientSession(connector=TCPConnector(ssl=False))
        
        self.trip_start_time = start_time
        self.max_travel_time = max_travel_time  
        self.latest_stop_time = latest_stop_time 
        self.stop_options_lists = []  

    
    async def get_stop_options_lists(self):
        return self.stop_options_lists

  
    async def search_route(self, start = None, goal = None, start_time = None):
        if start == None: start= self.start_station
        if goal == None: goal= self.goal_station
        if start_time == None: start_time = self.trip_start_time
        url = "https://navitime-route-totalnavi.p.rapidapi.com/route_transit"
        headers = {
            "X-RapidAPI-Key": RAPIDAPI_KEY,
            "X-RapidAPI-Host": "navitime-route-totalnavi.p.rapidapi.com",
        }

        querystring = {
            "unuse": "domestic_flight.superexpress_train.sleeper_ultraexpress.ultraexpress_train.express_train.semiexpress_train.shuttle_bus",
            "options": "railway_calling_at",
            "start": start,
            "goal": goal,
            "start_time": datetime_to_str(start_time)
        }

   
        async with self.session.get(url, headers=headers, params=querystring) as response:
            return await response.json()

   
    async def list_stop_stations(self):
        start = self.start_station
        start_time = self.trip_start_time

        while True:
       
            stop_options, terminal_station = await self.next_stop_stations(
                start, self.goal_station, start_time
            )
            if not stop_options:
                break
            self.stop_options_lists.append(stop_options)
            start = terminal_station
         
            start_time = start_time + datetime.timedelta(days=1)
          
            start_time = start_time.replace(hour=9, minute=0, second=0)

        return self.stop_options_lists

    
    async def next_stop_stations(self, start, goal, start_time):
        res = await self.search_route(start, goal, start_time)
        route = res["items"][0]
        stop_options = []

        travel_time = 0
        last_section_id = None
        terminal_station = None
        previous_start_time = start_time

        for section_id, section in enumerate(route["sections"]):
            if section["type"] == "move":
                section_to_time = str_to_datetime(section["to_time"])
       
                duration = (section_to_time - previous_start_time).total_seconds() // 60
                travel_time += duration
                previous_start_time = section_to_time

                
                if travel_time > self.max_travel_time or section_to_time.hour > self.latest_stop_time:
                    stop_options.append({
                        "name": route["sections"][section_id - 1]["name"],
                        "node_id": route["sections"][section_id - 1]["node_id"],
                        "coord": route["sections"][section_id - 1]["coord"],
                    })
                    last_section_id = section_id - 2
                    terminal_station = route["sections"][section_id - 1]["node_id"]
                    break

     
        if last_section_id is None:
            return [], terminal_station


        for station in route["sections"][last_section_id]["transport"]["calling_at"]:
            if "to_time" not in station:
                continue
            to_time = str_to_datetime(station["to_time"])
            terminal_to_time = str_to_datetime(route["sections"][last_section_id]["to_time"])
      
            if (terminal_to_time - to_time).total_seconds() < 40 * 60:
                stop_options.append({
                    "name": station["name"],
                    "node_id": station["node_id"],
                    "coord": station["coord"],
                })

        return stop_options, terminal_station

  
    @staticmethod
    async def create(start, goal, start_time, max_travel_time=60*6, latest_stop_time=19):
        instance = StopOptionsLister.__new__(StopOptionsLister)
        await instance.__init__(start, goal, start_time, max_travel_time, latest_stop_time)
        return instance


    async def close(self):
        await self.session.close()


async def save_to_json(data, file_path, indent=4, ensure_ascii=False):
    """
    Async function to save data to a JSON file (avoids blocking async loop)
    - data: The Python list/dict to save (your stop station list)
    - file_path: Full path to the JSON file (e.g., "stop_stations.json" or "data/stop_stations.json")
    - indent=4: Human-readable formatting
    - ensure_ascii=False: Preserve Japanese/non-ASCII characters (CRITICAL for your station names!)
    """
    await asyncio.to_thread(
        _sync_save_json,  
        data, file_path, indent, ensure_ascii
    )

def _sync_save_json(data, file_path, indent, ensure_ascii):
    # 1. If the folder doesn't exist (e.g., "data/"), create it
    folder = os.path.dirname(file_path)
    if folder and not os.path.exists(folder):
        os.makedirs(folder)  # Auto-create nested folders if needed
    # 2. Write data to JSON file (UTF-8 for Japanese)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=indent, ensure_ascii=ensure_ascii)
    print(f"✅ Data saved to JSON file: {os.path.abspath(file_path)}")
    
async def main():
    lister = await StopOptionsLister.create(
        "品川", "仙台", datetime.datetime(2026, 1, 1, 9, 0, 0)
    )
    
    route = await lister.search_route()
    await save_to_json(route, "./test_results.json")
    await lister.close()
    
    '''lister = await StopOptionsLister.create(
        "品川", "仙台", datetime.datetime(2020, 1, 1, 9, 0, 0)
    )

    stop_list = await lister.list_stop_stations()

    for item in stop_list[0]:
        print(item['name'])

    await lister.close()'''



if __name__ == "__main__":
    asyncio.run(main())