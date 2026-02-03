import pandas as pd

line_df = pd.read_csv("../../data/stations/line20230824free.csv")

JRline_df = line_df[(line_df["company_cd"] >= 1) & (line_df["company_cd"] <= 6)]

JRline_df.to_csv("../../data/stations/onlyJR_line20230824free.csv", index=False)