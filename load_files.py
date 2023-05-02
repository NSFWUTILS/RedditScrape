import os
import configparser
import concurrent.futures
import time
from queue import Queue
import subprocess
import gzip
import json
from compressed_json_wrapper import read_gzipped_json, GzippedJsonWriter
import re
from itertools import islice
from tqdm import tqdm
import threading

global giant_ass_list_to_download
giant_ass_list_to_download = Queue()


# Setup the configparser to read the config file named 'config'
config = configparser.ConfigParser()
config.read("config")
max_workers = int(config["CONFIG"]["MAX_WORKERS"])
root_folder = config["CONFIG"]["MEDIA_FOLDER"]
sleep_interval = int(config["CONFIG"]["SLEEP"])
last_character = root_folder[-1]
if last_character != "/":
    root_folder = root_folder + "/"

def process_file_entries(file_name_to_process):
    global giant_ass_list_to_download
    supported_domains_list = ["imgur.com", "redgifs.com", "gfycat.com"]
    futures = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        try:
            # Check if the file is empty
            if os.stat(file_name_to_process).st_size == 0:
                return
            
            for entry in read_gzipped_json(file_name_to_process):
                if any(domain in str(entry['url']) for domain in supported_domains_list):
                    entry_json_to_download = {
                        "author" : entry['author'],
                        "domain ": entry['domain'],
                        "post_id" : entry['id'],
                        "permalink" : entry['permalink'],
                        "subreddit_name" : entry['subreddit'],
                        "url": entry['url']
                    }
                    giant_ass_list_to_download.put(entry_json_to_download)
        except Exception as e:
            print(f"Error processing file {file_name_to_process}: {e}")



def get_files(json_folder):
    print(f"Loading files from {json_folder}")
    with concurrent.futures.ThreadPoolExecutor(max_workers=int(max_workers)) as executor:
        futures = []
        list_of_files = []
        for filename in os.listdir(json_folder):
            if filename.endswith('_raw.json.gz'):
                input_file_path = os.path.join(json_folder, filename)
                futures.append(executor.submit(process_file_entries, input_file_path))
        with tqdm(total=len(futures), desc="Processing Entries") as pbar:
            for future in concurrent.futures.as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    print(f"Error in get_files: {e}")
                pbar.update(1)
    print("\n",end="")
    giant_ass_list = []
    while not giant_ass_list_to_download.empty():
        item = giant_ass_list_to_download.get()
        giant_ass_list.append(item)
    return giant_ass_list


if __name__ == "__main__":
    get_files(root_folder)

    i = 0
    while i < 20:
        item = giant_ass_list_to_download.get()
        print(f"Download Sample: {item}")
        i += 1
    print(f"\nFinished. {giant_ass_list_to_download.qsize()} entries")
