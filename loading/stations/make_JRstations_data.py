import pandas as pd

JRline_df = pd.read_csv("../../data/stations/onlyJR_line20230824free.csv")
station_df = pd.read_csv("../../data/stations/station20230907free.csv")

JR_station_df = station_df[station_df["line_cd"].isin(JRline_df["line_cd"])]

JR_station_df.to_csv("../../data/stations/JR_station20230907free.csv", index=False)