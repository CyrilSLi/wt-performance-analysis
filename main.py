# Built-in modules
import calendar, csv, json, pickle, time
from datetime import datetime
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

csv_files = glob("Recent_Transit_On-Time_Performance_Data_*.csv") + glob("on_time_performance_*.csv")
if len(csv_files) == 0:
    raise SystemExit("No CSV files found.")
elif len(csv_files) == 1:
    csv_file = csv_files[0]
else:
    csv_file = csv_files[int(input("Num\tFile\n" + "\n".join(f"{i}\t{f}" for i, f in enumerate(csv_files)) + "\nSelect the CSV file to process: "))]

with open(csv_file) as f:
    try:
        wrong_service_ids = 0
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

            scheduled_time = row["Scheduled Time"]
            if (" " in scheduled_time): # Human-readable format
                time_struct = time.strptime(scheduled_time, "%Y %b %d %I:%M:%S %p")
            else: # ISO8601 format
                time_struct = datetime.fromisoformat(scheduled_time).timetuple()
            timestamp = int(calendar.timegm(time_struct))
            offset_timestamp = timestamp - 10800 # Service day starts at 3am

            schedule = next((i for i in schedule_starts if i < offset_timestamp), None)
            if schedule is None:
                raise ValueError(f"No schedule found for timestamp {offset_timestamp} (earliest schedule is {min(schedule_starts)})")

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

            day_of_week = (service_day - 1) % 7 # 0=Monday, 6=Sunday, 2017-01-01 was a Sunday
            if (day_of_week < 5 and service_id != 1) or (day_of_week == 5 and service_id != 2) or (day_of_week == 6 and service_id != 3):
                # print(f"Skipping trip {trip_id} on service day {service_day} (day of week {day_of_week}) with service_id {service_id}")
                wrong_service_ids += 1
                continue # Skip trips that don't match the day of the week

            stop_times[schedule].setdefault((trip_id, service_day), []).append((stop_sequence, timestamp - int(row["Deviation"].replace(",", "")), int(row["Stop Number"]), direction_index, time_struct.tm_hour))

    except KeyboardInterrupt:
        pass # Allow early exit for debugging

print(f"Found and excluded {wrong_service_ids} rows with wrong day of week")

for schedule_start in stop_times:
    stop_segs = {}
    same_stop_segs = set()
    for trip_and_day in tqdm(stop_times[schedule_start], desc=f"Processing schedule {schedule_start}", total=len(stop_times[schedule_start]), mininterval=0.5):
        trip_stop_times = sorted(stop_times[schedule_start][trip_and_day], key=lambda x: x[0])
        for prev, curr in zip(trip_stop_times, trip_stop_times[1:]):

            if prev[2] == curr[2]:
                same_stop_segs.add(f"{prev[2]}-{curr[2]}-{curr[3]}")
                continue # Skip segments that start and end at the same stop

            stop_segs.setdefault(
                f"{prev[2]}-{curr[2]}-{curr[3]}", {}             # stop_from-stop_to-direction_index
            ).setdefault(
                trip_and_day[1], [[] for _ in range(24)]         # service_day, list of 24 lists for each hour
            )[(curr[4] - 3) % 24].append(str(curr[1] - prev[1])) # [3am, 4am, ..., 2am]

    print(f"Found and excluded {len(same_stop_segs)} same-stop segments")

    for seg_key in stop_segs:
        for service_day in stop_segs[seg_key]:
            stop_segs[seg_key][service_day] = "|".join(",".join(x) for x in stop_segs[seg_key][service_day])

    with open(f".cache/stop_segs-{schedule_start}.json", "w") as f:
        json.dump(stop_segs, f, sort_keys=True, indent=1) # separators=(",", ":"))

    print(f"Wrote .cache/stop_segs-{schedule_start}.json with {len(stop_segs)} stop segments")