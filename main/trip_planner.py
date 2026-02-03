import pandas as pd
import datetime
import stop_options
from geopy.distance import geodesic
import os

print("Current Directory:", os.getcwd())

import datetime
import tkinter as tk
from tkinter import ttk
from tkcalendar import DateEntry

def pick_datetime():
    root = tk.Tk()
    root.title("出発時刻を選択")
    # 1. 核心修复：把窗口调大，从380x180改成550x220，确保所有组件都能放下
    root.geometry("550x220")
    root.resizable(False, False)

    # 窗口置顶（保留之前的修复）
    root.lift()
    root.attributes('-topmost', True)
    root.after(100, lambda: root.attributes('-topmost', False))

    # 样式设置
    style = ttk.Style(root)
    style.configure("TLabel", font=("Arial", 12))
    style.configure("TCombobox", font=("Arial", 12))
    style.configure("TButton", font=("Arial", 12))

    # 2. 优化布局：增加组件间距，避免拥挤
    ttk.Label(root, text="日付：").grid(row=0, column=0, padx=15, pady=30, sticky="w")
    date_picker = DateEntry(root, date_pattern="yyyy/mm/dd", width=16)
    date_picker.grid(row=0, column=1, padx=10, pady=30)

    ttk.Label(root, text="時間：").grid(row=0, column=2, padx=15, pady=30, sticky="w")
    hour_list = [f"{h:02d}" for h in range(24)]
    hour_combo = ttk.Combobox(root, values=hour_list, width=6)
    hour_combo.grid(row=0, column=3, padx=10, pady=30)
    hour_combo.current(9)

    ttk.Label(root, text="分：").grid(row=0, column=4, padx=15, pady=30, sticky="w")
    min_list = [f"{m:02d}" for m in range(0, 60, 5)]
    min_combo = ttk.Combobox(root, values=min_list, width=6)
    min_combo.grid(row=0, column=5, padx=10, pady=30)
    min_combo.current(0)

    select_str = None
    def confirm():
        nonlocal select_str
        date_str = date_picker.get()
        hour = hour_combo.get()
        minute = min_combo.get()
        select_str = f"{date_str} {hour}:{minute}"
        root.destroy()

    ttk.Button(root, text="確認", command=confirm).grid(row=1, column=0, columnspan=6, pady=10)
    root.mainloop()
    return select_str


class TripPlanner:
    def __init__(self):
        self.nearest_station_df = pd.read_csv("../data/hotels/nearest_station.csv")
        self.hotels_scores_df = pd.read_csv("../data/hotels/hotels_scores.csv")

    # returns a list of hotel codes which nearest station is the given station
    def search_hotels_from_station(
        self, station_name, station_latitude, station_longitude
    ):
        result = self.nearest_station_df[
            self.nearest_station_df["nearest_station_name"] == station_name
        ]["hotelcode"].tolist()
        # if there is no station with the given name, search hotels within 100 meters from the given latitude and longitude
        if not result:
            distance = self.nearest_station_df.apply(
                lambda row: geodesic(
                    (row["nearest_station_latitude"], row["nearest_station_longitude"]),
                    (station_latitude, station_longitude),
                ).m
                if not row.isnull().any()
                else 1000,
                axis=1,
            )
            result = self.nearest_station_df[distance <= 100]["hotelcode"].tolist()
        return result

    # returns a dataframe of hotels with scores
    def get_hotels_scores(self, hotels_list):
        return self.hotels_scores_df[
            self.hotels_scores_df["hotelcode"].isin(hotels_list)
        ]

    # returns a tuple of station score and a dataframe of top 5 hotels with scores
    def get_station_score(self, station_name, station_latitude, station_longitude):
        hotels_list = self.search_hotels_from_station(
            station_name, station_latitude, station_longitude
        )
        nearby_hotels_with_scores_df = self.get_hotels_scores(hotels_list)
        sorted_hotels_with_scores_df = nearby_hotels_with_scores_df.sort_values(
            "score", ascending=False
        )
        # station score is the average of the top 5 hotels' scores
        if len(sorted_hotels_with_scores_df) < 5:
            data = [["none", 0] for x in range(5)]
            indices = [
                i
                for i in range(
                    len(sorted_hotels_with_scores_df),
                    len(sorted_hotels_with_scores_df) + 5,
                )
            ]
            df = pd.DataFrame(data, columns=["hotelcode", "score"], index=indices)
            sorted_hotels_with_scores_df = pd.concat([sorted_hotels_with_scores_df, df])

        station_score = sorted_hotels_with_scores_df["score"].head(5).mean()
        return station_score, sorted_hotels_with_scores_df["hotelcode"].head(5).tolist()

    # returns a tuple of best station name and top 5 hotels near the station
    def get_best_station(self, stations_names, latitudes, longitudes):
        best_score = 0
        best_station_name = None
        best_hotels = None
        for station_name, latitude, longitude in zip(
            stations_names, latitudes, longitudes
        ):
            station_score, hotels = self.get_station_score(
                station_name, latitude, longitude
            )
            if station_score > best_score:
                best_score = station_score
                best_station_name = station_name
                best_hotels = hotels
        return best_station_name, best_hotels

    # return a list of stops
    # each stop is a tuple of station name and top 5 hotels near the station
    def plan_trip(self, start, goal, start_time):
        stops_lister = stop_options.StopOptionsLister(start, goal, start_time)
        stops_options_list = stops_lister.list_stop_stations()
        suggest_stops = []
        for stops_options in stops_options_list:
            station_names = [stop["name"] for stop in stops_options]
            station_latitudes = [stop["coord"]["lat"] for stop in stops_options]
            station_longitudes = [stop["coord"]["lon"] for stop in stops_options]
            suggest_stops.append(
                self.get_best_station(
                    station_names, station_latitudes, station_longitudes
                )
            )

        return suggest_stops


def test():
    start = "品川"
    goal = "仙台"
    start_time = pick_datetime()  
    start_time = datetime.datetime.strptime(start_time, "%Y/%m/%d %H:%M")  
    planner = TripPlanner()
    suggests = planner.plan_trip(start, goal, start_time)
  
    hotel_df = pd.read_csv("../data/hotels/KNT_hotels.csv")
    # prints suggested stops
    for i, suggest in enumerate(suggests):
        print("{}泊目".format(i + 1))
        print(" 駅名: {}".format(suggest[0]))
        print(" ホテル")
        for hotelcode in suggest[1]:
            if hotelcode == "none":
                continue
            print(
                "  {}".format(
                    hotel_df[hotel_df["hotelcode"] == hotelcode]["name"].values[0]
                )
            )
           
        print("*************************************")

if __name__ == "__main__":
    test()
