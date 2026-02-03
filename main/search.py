import requests
import datetime
import os
from dotenv import load_dotenv
load_dotenv()

RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")

# 兼容带/不带时区的时间解析
def datetime_to_str(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%S")

def str_to_datetime(time_str):
    try:
        # 优先解析带时区的格式（API 标准返回）
        return datetime.datetime.strptime(time_str, "%Y-%m-%dT%H:%M:%S+09:00")
    except ValueError:
        # 兼容无时区的格式
        return datetime.datetime.strptime(time_str, "%Y-%m-%dT%H:%M:%S")

class StopOptionsLister:
    def __init__(
        self, start, goal, start_time, max_travel_time=60 * 6, latest_stop_time=19
    ):
        self._headers = {
            "X-RapidAPI-Key": RAPIDAPI_KEY,
            "X-RapidAPI-Host": "navitime-transport.p.rapidapi.com",
        }
        # 修复1：站点ID获取增加容错（避免无结果时报错）
        self.start_station = self._station_name_to_id(start)
        self.goal_station = self._station_name_to_id(goal)
        if not (self.start_station and self.goal_station):
            raise ValueError("出发/到达站搜索失败，请检查站点名称")

        self.trip_start_time = start_time
        self.max_travel_time = max_travel_time  # 最大旅行时间（分钟）
        self.latest_stop_time = latest_stop_time  # 最晚停留时间（小时）
        self.stop_options_lists = []  # 每日停留站点列表

    def _station_name_to_id(self, station_name):
        """站点名称转ID（增加空值校验）"""
        url = "https://navitime-transport.p.rapidapi.com/transport_node"
        querystring = {"word": station_name}
        try:
            response = requests.get(url, headers=self._headers, params=querystring)
            response.raise_for_status()  # 捕获HTTP错误
            items = response.json().get("items", [])
            return items[0]["id"] if items else None
        except (requests.exceptions.RequestException, IndexError, KeyError):
            print(f"警告：站点「{station_name}」未找到，请核对名称")
            return None

    def get_stop_options_lists(self):
        return self.stop_options_lists

    # 搜索路线（严格按API规范解析字段）
    def search_route(self, start, goal, start_time):
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
        try:
            response = requests.get(url, headers=headers, params=querystring)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"路线搜索失败：{e}")
            return {"items": []}

    # 生成每日停留站点列表
    def list_stop_stations(self):
        start = self.start_station
        start_time = self.trip_start_time

        while True:
            stop_options, terminal_station = self.next_stop_stations(
                start, self.goal_station, start_time
            )
            if not stop_options or not terminal_station:
                break
            self.stop_options_lists.append(stop_options)
            # 修复2：datetime.replace返回新对象，需重新赋值
            start = terminal_station
            start_time = start_time + datetime.timedelta(days=1)
            start_time = start_time.replace(hour=9, minute=0, second=0)

        return self.stop_options_lists

    # 获取下一批停留站点（核心字段修复）
    def next_stop_stations(self, start, goal, start_time):
        res = self.search_route(start, goal, start_time)
        # 容错：无路线结果时直接返回空
        if not res.get("items"):
            return [], None
        route = res["items"][0]
        stop_options = []
        travel_time = 0
        last_section_id = None
        terminal_station = None
        previous_start_time = start_time

        for section_id, section in enumerate(route.get("sections", [])):
            # 仅处理「移动」类型的section
            if section.get("type") != "move":
                continue
            # 修复3：使用API规范的departure/arrival字段
            departure = section.get("departure", {})
            arrival = section.get("arrival", {})
            # 过滤无时间信息的无效section
            if not departure.get("time") or not arrival.get("time"):
                continue

            # 计算行程耗时
            section_to_time = str_to_datetime(arrival["time"])
            duration = (section_to_time - previous_start_time).total_seconds() // 60
            travel_time += duration
            previous_start_time = section_to_time

            # 判断是否需要停留
            if travel_time > self.max_travel_time or section_to_time.hour > self.latest_stop_time:
                # 取上一个section的站点作为停留点
                prev_section = route["sections"][section_id - 1] if section_id > 0 else {}
                prev_arrival = prev_section.get("arrival", {})
                if prev_arrival.get("name") and prev_arrival.get("node_id"):
                    stop_options.append({
                        "name": prev_arrival["name"],
                        "node_id": prev_arrival["node_id"],
                        "coord": prev_arrival.get("coord", {"lat": None, "lon": None})
                    })
                    last_section_id = section_id - 2
                    terminal_station = prev_arrival["node_id"]
                break

        # 补充途经站（过滤无效calling_at数据）
        if last_section_id is not None and last_section_id >= 0:
            transport = route["sections"][last_section_id].get("transport", {})
            calling_at = transport.get("calling_at", [])
            terminal_section = route["sections"][last_section_id]
            terminal_to_time = str_to_datetime(terminal_section["arrival"]["time"])
            
            for station in calling_at:
                if not station.get("to_time"):
                    continue
                to_time = str_to_datetime(station["to_time"])
                # 40分钟内的途经站加入候选
                if (terminal_to_time - to_time).total_seconds() < 40 * 60:
                    stop_options.append({
                        "name": station["name"],
                        "node_id": station["node_id"],
                        "coord": station.get("coord", {"lat": None, "lon": None})
                    })

        # 去重（避免重复站点）
        stop_options = [dict(t) for t in {tuple(d.items()) for d in stop_options}]
        return stop_options, terminal_station

# 测试代码
def main():
    try:
        lister = StopOptionsLister(
            "品川", "仙台", datetime.datetime(2020, 1, 1, 9, 0, 0)
        )
        stop_lists = lister.list_stop_stations()
        if not stop_lists:
            print("未找到符合条件的停留站点")
        else:
            for i, stops in enumerate(stop_lists):
                print(f"第{i+1}天停留候选站点：")
                for stop in stops:
                    print(f"  - {stop['name']} (ID: {stop['node_id']})")
    except ValueError as e:
        print(e)

if __name__ == "__main__":
    main()