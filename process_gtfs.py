# Built-in modules
import calendar, csv, json, os, pickle, time
from base64 import b64encode
from glob import glob
from zipfile import ZipFile

# Third-party modules
from tqdm import tqdm

from utils import base64_int, line_count



for gtfs_zip in glob("mdb-717-*.zip"):
    for i in glob(".gtfs/*"):
        if i != ".gtfs/.gitkeep":
            os.remove(i)
    with ZipFile(gtfs_zip) as zf:
        zf.extractall(".gtfs")

    with open(".gtfs/calendar.txt") as f_calendar:
        start_date = next(csv.DictReader(f_calendar))["start_date"]
        start_ts = int(calendar.timegm(time.strptime(start_date, "%Y%m%d")))

    directions = set()
    with open(".gtfs/trips.txt") as f_trips:
        for row in tqdm(csv.DictReader(f_trips), total=line_count(".gtfs/trips.txt")):
            for i in range(1, 4):
                directions.add(f'{i}-{row["route_id"]} {row["trip_headsign"]}')
    directions = sorted(directions)

    with open(f".cache/directions-{start_ts}.txt", "w") as f:
        f.write("\n".join(directions))

    trips = {}
    with open(".gtfs/trips.txt") as f_trips:
        for row in tqdm(csv.DictReader(f_trips), total=line_count(".gtfs/trips.txt")):
            service_id = int(row["service_id"])
            if service_id > 3:
                continue # Skip trips that don't run on regular days
            trips[row["trip_id"]] = directions.index(f'{service_id}-{row["route_id"]} {row["trip_headsign"]}')

    # Ensure that trip_keys are unique for duplicate stops by being longer than all non-duplicate trip IDs.
    trip_id_len_variation = max(len(str(trip_id)) for trip_id in trips.keys()) - min(len(str(trip_id)) for trip_id in trips.keys())
    dupe_stops_prefix = "0" * trip_id_len_variation

    stop_trips, stops_per_trip, dupe_stops = {}, {}, {}
    with open(".gtfs/stop_times.txt") as f_stop_times:
        for row in tqdm(csv.DictReader(f_stop_times), total=line_count(".gtfs/stop_times.txt")):
            if row["trip_id"] not in trips:
                continue # Skip trips that don't run on regular days
            arrival_time = f'{(int(row["arrival_time"][:2]) % 24):02d}{row["arrival_time"][2:].replace(":", "")}'
            stop_id = row["stop_id"]
            dir_index = trips[row["trip_id"]]

            stops_in_trip = stops_per_trip.setdefault(row["trip_id"], [])
            if stop_id in stops_in_trip:
                if f"{stop_id}{arrival_time}{dir_index}" in stop_trips:
                    raise NotImplementedError(f"{directions[dir_index]} has undistinguishable duplicate stops times at {stop_id}")
                dupe_level = stops_in_trip.count(stop_id)
                if dupe_level > 9:
                    raise NotImplementedError(f"Stop {stop_id} in trip {row['trip_id']} has more than 9 duplicates")

                dupe_stops[stop_id] = max(dupe_stops.get(stop_id, 0), dupe_level)
                stop_id = int(f"{dupe_level}{dupe_stops_prefix}{stop_id}")

            stops_in_trip.append(row["stop_id"]) # Use original stop_id to track duplicates

            trip_key = int(f"{stop_id}{arrival_time}{dir_index}")
            if trip_key in stop_trips:
                raise ValueError(f"Duplicate trip key: {trip_key}")
            stop_trips[trip_key] = (base64_int(row["trip_id"]), int(row["stop_sequence"]))
    
    with open(f".cache/stop_trips-{start_ts}.pkl", "wb") as f:
        pickle.dump((directions, stop_trips, dupe_stops, dupe_stops_prefix), f)

    with open(".gtfs/stops.txt") as f_stops, open(f".cache/stops-{start_ts}.json", "w") as f:
        stops = {}
        for row in csv.DictReader(f_stops):
            stops[row["stop_id"]] = [row["stop_name"], float(row["stop_lat"]), float(row["stop_lon"])]
            if row["stop_id"] in dupe_stops:
                for level in range(1, dupe_stops[row["stop_id"]] + 1):
                    dupe_stop_id = f"{level}{dupe_stops_prefix}{row['stop_id']}"
                    stops[dupe_stop_id] = [
                        f"{row['stop_name']} (copy {level})",
                        float(row["stop_lat"]),
                        float(row["stop_lon"])
                    ]
                    print(f"Added duplicate stop {dupe_stop_id} for {row['stop_id']}")
        json.dump(stops, f, indent=1, sort_keys=True)