import pandas as pd
from geopy.distance import geodesic


# finds nearest station from the given latitude and longitude
# station_df: dataframe of stations that has columns "station_name", "latitude", "longitude"
def find_nearest_station(latitude, longitude, station_df):
    # calculates distance between two points
    # if the differece of latitude and longitude is more than or equal 0.07, skip the calculation and return 500000
    distances = station_df[["latitude", "longitude"]].apply(
        lambda row: geodesic(
            (latitude, longitude), (row["latitude"], row["longitude"])
        ).m
        if abs(latitude - row["latitude"]) < 0.07
        and abs(longitude - row["longitude"]) < 0.07
        else 500000,
        axis=1,
    )
    nearest_station_index = distances.idxmin()
    nearest_station = station_df.iloc[nearest_station_index]
    if distances[nearest_station_index] >= 500000:
        return (None, None, None, None)

    return (
        nearest_station["station_name"],
        nearest_station["latitude"],
        nearest_station["longitude"],
        distances[nearest_station_index],
    )


def main():
    hotels_df = pd.read_csv("../../data/hotels/KNT_hotels.csv")
    station_df = pd.read_csv("../../data/stations/JR_station20230907free.csv")

    new_station_df = pd.DataFrame()
    new_station_df["station_name"] = station_df["station_name"]
    new_station_df["latitude"] = station_df["lat"]
    new_station_df["longitude"] = station_df["lon"]

    nearest_station_tupple = hotels_df.apply(
        lambda row: find_nearest_station(
            row["latitude"], row["longitude"], new_station_df
        )
        if not row[["latitude", "longitude"]].isnull().any()
        else (None, None, None, None),
        axis=1,
    )

    nearest_station_df = pd.DataFrame(
        nearest_station_tupple.tolist(),
        columns=[
            "nearest_station_name",
            "nearest_station_latitude",
            "nearest_station_longitude",
            "distance",
        ],
    )
    nearest_station_df["hotelcode"] = hotels_df["hotelcode"]
    nearest_station_df["hotelname"] = hotels_df["name"]

    nearest_station_df.to_csv("../../data/hotels/nearest_station.csv", index=False)


if __name__ == "__main__":
    main()
