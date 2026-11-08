# Built-in modules
import json, re, time
from glob import glob

# 3rd-party modules
import brotli

perf_data = {
    "updated": int(time.time()),
    "stops": {},
    "schedules": {}
}

for i in glob(".cache/stop_segs-*.json"):
    schedule = int(i.split("-")[-1].split(".")[0])
    schedule_obj = perf_data["schedules"].setdefault(schedule, {
        "services": ["Weekday", "Saturday", "Sunday"],
        "directions": {},
        "stop_segs": {}
    })

    orig_stop_segs = json.load(open(i))
    stop_segs, stops_used = {}, set()
    for seg_key in orig_stop_segs:
        stop_from, stop_to, dir_index = seg_key.split("-")
        stops_used.update((stop_from, stop_to))
        stop_segs.setdefault(stop_from, {}).setdefault(stop_to, {})[dir_index] = {day: hours.rstrip("|") for day, hours in orig_stop_segs[seg_key].items()}
    schedule_obj["stop_segs"] = stop_segs

    orig_directions = open(f".cache/directions-{schedule}.txt").read().splitlines()
    schedule_obj["directions"] = [i.lstrip("1-") for i in orig_directions if i.startswith(("1-"))]

    orig_stops = json.load(open(f".cache/stops-{schedule}.json"))
    print(f"{len(stops_used)}/{len(orig_stops)} stops used in schedule {schedule}")
    perf_data["stops"].update({stop_id: orig_stops[stop_id] for stop_id in stops_used})

dump = json.dumps(perf_data, separators=(",", ":"), sort_keys=True)
dump = "window.perfData = " + re.sub(r'"(\w+)":', r"\1:", dump) # Remove quotes from single-word keys (JS object minification)

with open(".cache/data.js", "w") as f:
    f.write(dump)

if input("Compress data.js with Brotli? (y/n) ").lower() == "y":
    with open(".cache/data.js.br", "wb") as f:
        f.write(brotli.compress(dump.encode("utf-8"), mode=brotli.MODE_TEXT, quality=11, lgwin=24))