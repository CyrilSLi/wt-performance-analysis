# Built-in modules
import json, re
from glob import glob

for i in glob(".cache/stop_segs-*.json"):
    orig = json.load(open(i))
    new = {}
    for seg_key in orig:
        stop_from, stop_to, dir_index = seg_key.split("-")
        new.setdefault(stop_from, {}).setdefault(stop_to, {})[dir_index] = {day: hours.rstrip("|") for day, hours in orig[seg_key].items()}

    dump = json.dumps(new, separators=(",", ":"))
    dump = re.sub(r'"(\w+)":', r"\1:", dump) # Remove quotes from single-word keys (JS object minification)

    with open(i.replace(".json", ".js"), "w") as f:
        f.write("window.stopSegs = ")
        f.write(dump)