import subprocess
from base64 import b64encode

def line_count(path):
    return int(subprocess.check_output(["wc", "-l", path]).decode("utf-8").strip().split()[0]) - 1

def base64_int(n):
    return b64encode(int(n).to_bytes((int(n).bit_length() + 7) // 8, "big")).decode().rstrip("=")