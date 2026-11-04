# Built-in modules
import json, re
from glob import glob

from utils import base64_int

for i in glob(".cache/stop_segs-*.json"):
    orig = json.load(open(i))
    new = {}
    for seg_key in orig:
        stop_from, stop_to, dir_index = seg_key.split("-")
        new_seg = new.setdefault(base64_int(stop_from), {}).setdefault(base64_int(stop_to), {}).setdefault(base64_int(dir_index), {})
        for day in orig[seg_key]:
            hours = orig[seg_key][day].rstrip("|").split("|")
            new_hours = []
            for hour in hours:
                if hour:
                    new_hours.append(",".join(f'{trip.split("_")[0]}_{base64_int(trip.split("_")[1])}' for trip in hour.split(",")))
                else:
                    new_hours.append("")
            hours = "|".join(new_hours)
            new_seg[base64_int(day)] = hours

    dump = json.dumps(new, separators=(",", ":"))
    dump = re.sub(r'"(\w+)":', r"\1:", dump) # Remove quotes from single-word keys (JS object minification)

    with open(i.replace(".json", ".js"), "w") as f:
        f.write("window.stopSegs = ")
        f.write(dump)