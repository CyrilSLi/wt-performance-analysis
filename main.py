# Built-in modules
import calendar, csv, json, pickle, time
from glob import glob

# Third-party modules
from tqdm import tqdm

from utils import line_count



schedule_starts = []
all_info = {}
for i in reversed(sorted(glob(".cache/stop_trips-*.pkl"))):
    schedule_start = int(i.split("-")[-1].split(".")[0])
    schedule_starts.append(schedule_start)
    all_info[schedule_start] = pickle.load(open(i, "rb"))




stop_times = {schedule_start: {} for schedule_start in schedule_starts}

csv_file = glob("Recent_Transit_On-Time_Performance_Data_*.csv")[0]
with open(csv_file) as f:
    try:
        for row in tqdm(csv.DictReader(f), total=line_count(csv_file), mininterval=0.5):
            match row["Day Type"]:
                case "Weekday":
                    service_id = 1
                case "Saturday":
                    service_id = 2
                case "Sunday":
                    service_id = 3
                case _:
                    continue # Skip holidays and other irregular days

            time_struct = time.strptime(row["Scheduled Time"], "%Y %b %d %I:%M:%S %p")
            timestamp = int(calendar.timegm(time_struct))
            offset_timestamp = timestamp - 10800 # Service day starts at 3am
            schedule = next((i for i in schedule_starts if i < offset_timestamp), None)

            directions, stop_trips = all_info[schedule]
        
            direction_key = f'{service_id}-{row["Route Number"]} {row["Route Destination"]}'
            if direction_key not in directions:
                if direction_key != "1-211 ": # Hardcoded case for standby trips
                    raise ValueError(f"Unknown direction: {direction_key}")
                continue
            direction_index = directions.index(direction_key)

            trip_key = int(f'{row["Stop Number"]}{time_struct.tm_hour:02d}{time_struct.tm_min:02d}{time_struct.tm_sec:02d}{direction_index}')
            if trip_key not in stop_trips:
                raise ValueError(f"Unknown trip: {trip_key}")
            trip_id, stop_sequence = stop_trips[trip_key]

            service_day = offset_timestamp // 86400 - 17167 # Days since 2017-01-01 (first year with data)
            stop_times[schedule].setdefault((trip_id, service_day), []).append((stop_sequence, timestamp + int(row["Deviation"].replace(",", "")), int(row["Stop Number"]), direction_index, time_struct.tm_hour))

    except KeyboardInterrupt:
        pass # Allow early exit for debugging

for schedule_start in stop_times:
    stop_segs = {}
    impossible_segs = set()
    for trip_and_day in stop_times[schedule_start]:
        trip_stop_times = sorted(stop_times[schedule_start][trip_and_day], key=lambda x: x[0])
        for prev, curr in zip(trip_stop_times, trip_stop_times[1:]):
            if prev[2] == curr[2]:
                impossible_segs.add(f"{prev[2]}-{curr[2]}-{curr[3]}")
                continue # Skip segments that start and end at the same stop
            stop_segs.setdefault(
                f"{prev[2]}-{curr[2]}-{curr[3]}", {}             # stop_from-stop_to-direction_index
            ).setdefault(
                trip_and_day[1], [[] for _ in range(24)]         # service_day, list of 24 lists for each hour
            )[(curr[4] - 3) % 24].append(str(curr[1] - prev[1])) # [3am, 4am, ..., 2am]

    print(f"Found {len(impossible_segs)} impossible segments")

    for seg_key in stop_segs:
        for service_day in stop_segs[seg_key]:
            stop_segs[seg_key][service_day] = "|".join(",".join(x) for x in stop_segs[seg_key][service_day])

    with open(f".cache/stop_segs-{schedule_start}.json", "w") as f:
        json.dump(stop_segs, f, sort_keys=True, indent=1) # separators=(",", ":"))

    print(f"Wrote .cache/stop_segs-{schedule_start}.json with {len(stop_segs)} stop segments")