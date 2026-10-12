import subprocess

def line_count(path):
    return int(subprocess.check_output(["wc", "-l", path]).decode("utf-8").strip().split()[0]) - 1