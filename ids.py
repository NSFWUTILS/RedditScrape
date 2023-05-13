#!/usr/bin/env python

import configparser
from pathlib import Path

from compressed_json_wrapper import read_gzipped_json

config = configparser.ConfigParser()
config.read("config")
root_folder = config["CONFIG"]["MEDIA_FOLDER"]


def process_entries(file):
    ids = []
    try:
        if Path(file).stat().st_size == 0:
            return None
        for entry in read_gzipped_json(file):
            ids.append(entry["id"])
        return ids
    except Exception as e:
        print(f"Error processing file {file}: {e}")


def get_ids(folder):
    ids = []
    num = 1
    for filename in Path(folder).iterdir():
        if str(filename).endswith("_raw.json.gz"):
            print(f"{num:04}: Processing {filename}")
            ids.extend(process_entries(filename))
            num += 1
    with Path(folder, "ids.txt").open(mode="a+t") as id_file:
        id_file.write("\n".join(map(str, ids)))


def main():
    json_folder = root_folder + "json"
    print(f"Saving ID file to {Path(json_folder, 'ids.txt')}")
    get_ids(json_folder)


if __name__ == "__main__":
    main()
