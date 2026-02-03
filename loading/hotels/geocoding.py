import pandas as pd
import urllib
import requests
from geopy.geocoders import GoogleV3


# gets latitude and longitude from address using GSI API
def get_coordinates_GSI(address):
    make_url = "https://msearch.gsi.go.jp/address-search/AddressSearch?q="
    s_quote = urllib.parse.quote(address)
    response = requests.get(make_url + s_quote)
    return (
        response.json()[0]["geometry"]["coordinates"][1],
        response.json()[0]["geometry"]["coordinates"][0],
    )


# gets latitude and longitude from address using geopy with google maps API
geolocator = GoogleV3(api_key="AIzaSyDn_0kPMFPXkPXMtYzVqlssfWbjV9pzs-M")


def get_coordinates_geopy(place_name):
    global geolocator

    location = geolocator.geocode(place_name)
    if location is None:
        return None, None
    return location.latitude, location.longitude


def count_no_coordnate_hotels():
    hotels_df = pd.read_csv("data/hotels/KNT_hotels.csv")
    return hotels_df["latitude"].isnull().sum()


def main():
    hotels_df = pd.read_csv("../../data/hotels/KNT_hotels.csv")

    # if latitude and longitude are not given, get them from address
    hotels_coordinate_tupple = hotels_df[["name", "latitude", "longitude"]].apply(
        lambda row: get_coordinates_geopy(row["name"])
        if row.isnull().any()
        else (row["latitude"], row["longitude"]),
        axis=1,
    )
    hotels_df[["latitude", "longitude"]] = pd.DataFrame(
        hotels_coordinate_tupple.tolist(), columns=["latitude", "longitude"]
    )

    hotels_df.to_csv("../../data/hotels/KNT_hotels.csv", index=False)


def test():
    hotels_df = pd.read_csv("../../data/hotels/test_hotels.csv")

    # if latitude and longitude are not given, get them from address
    hotels_coordinate_tupple = hotels_df[["name", "latitude", "longitude"]].apply(
        lambda row: get_coordinates_geopy(row["name"])
        if row.isnull().any()
        else (row["latitude"], row["longitude"]),
        axis=1,
    )
    hotels_df[["latitude", "longitude"]] = pd.DataFrame(
        hotels_coordinate_tupple.tolist(), columns=["latitude", "longitude"]
    )

    hotels_df.to_csv("../../data/hotels/test_res_hotels.csv", index=False)


if __name__ == "__main__":
    main()
    # test()
