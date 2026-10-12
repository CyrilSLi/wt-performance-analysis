# Built-in modules
import calendar, csv, os, pickle, time
from glob import glob
from zipfile import ZipFile

# Third-party modules
from tqdm import tqdm

from utils import line_count



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

    stop_trips = {}
    with open(".gtfs/stop_times.txt") as f_stop_times:
        for row in tqdm(csv.DictReader(f_stop_times), total=line_count(".gtfs/stop_times.txt")):
            if row["trip_id"] not in trips:
                continue # Skip trips that don't run on regular days
            arrival_time = f'{(int(row["arrival_time"][:2]) % 24):02d}{row["arrival_time"][2:].replace(":", "")}'

            trip_key = int(f"{row['stop_id']}{arrival_time}{trips[row['trip_id']]}")
            if trip_key in stop_trips:
                raise ValueError(f"Duplicate trip key: {trip_key}")
            stop_trips[trip_key] = (int(row["trip_id"]), int(row["stop_sequence"]))
    
    with open(f".cache/stop_trips-{start_ts}.pkl", "wb") as f:
        pickle.dump((directions, stop_trips), f)