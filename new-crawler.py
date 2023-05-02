import os
import configparser
import praw
from utils import clean_title
import concurrent.futures
import requests
import time
from queue import Queue
from requests.adapters import HTTPAdapter
from requests.sessions import Session
import subprocess
import csv
import gzip
import json
from compressed_json_wrapper import read_gzipped_json, GzippedJsonWriter
import re
from itertools import islice
from tqdm import tqdm
from load_files import get_files


# Setup the configparser to read the config file named 'config'
config = configparser.ConfigParser()
config.read("config")
max_workers = int(config["CONFIG"]["MAX_WORKERS"])
root_folder = config["CONFIG"]["MEDIA_FOLDER"]
sleep_interval = int(config["CONFIG"]["SLEEP"])
last_character = root_folder[-1]
if last_character != "/":
    root_folder = root_folder + "/"


global download_errors
global download_success
global skipped_files
global duplicate_urls
global rate_limit_queue
global file_entry_queue
file_entry_queue = Queue()
rate_limit_queue = Queue()
download_success = Queue()
download_errors = Queue()
skipped_files = Queue()
duplicate_urls = Queue()


def update_progress():
    global download_entries
    total_urls = len(download_entries)
    download_counter = download_success.qsize() + download_errors.qsize() + skipped_files.qsize()
    progress = (download_counter / total_urls) * 100


def gallery_download(download_item):
    global root_folder
    #print(f"Gallery processing entry: {download_item}", flush=True)
    reddit_permalink = download_item['permalink']
    post_title = f"{download_item['post_id']}-{reddit_permalink.split('/')[-2]}"
    if download_item['author'] == "[deleted]":
        post_author = "deleted"
    else:
        post_author = download_item['author']
    file_name = f"{download_item['post_id']}-{post_author}-{post_title}"
    subreddit_folder = root_folder + "subreddits/" + download_item['subreddit_name'] +"/"
    gallery_command = f'python -m gallery_dl -D {subreddit_folder} -f "{post_title}.{{extension}}" {download_item["url"]} '
    result = subprocess.run(gallery_command, shell=True, text=True, capture_output=True)
    download_file_name = f"{subreddit_folder}{post_title}"
    if "#" in str(result.stdout):
        log_entry = f"Skipped,permalink:{download_item['permalink']}, file:{download_file_name}"
        skipped_files.put(log_entry)
        return log_entry
    elif root_folder in str(result.stdout):
        log_entry = f"Downloaded,permalink:{download_item['permalink']}, file:{download_file_name}"
        download_success.put(log_entry)
        return log_entry
    if result.stderr:
        if "FileExistsError" not in str(result.stderr) and "410 Gone" not in str(result.stderr):
            if "429" in str(result.stderr):
                rate_limit_queue.put(download_item['url'])
                time.sleep(60)
            if "FileExistsError" not in str(result.stderr):
                log_entry = f"Error,permalink:{download_item['permalink']},file:{download_file_name},error:{result.stderr}"
                download_errors.put(log_entry)
                return log_entry



def process_file_entries(file_name_to_process):
    global my_download_counter
    global download_urls
    global file_entry_queue
    print(f"Threaded processing of {file_name_to_process}",flush=True)
    futures = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        for entry in read_gzipped_json(file_name_to_process):
            my_download_counter += 1
            # Gallery-dl only supports certain domains, and I'm only after the biggest ones
            # This will ensure only supported domains are processed
            # It will also help filter out a ton of the junk spam etc
            supported_domains_list = ["imgur.com", "redgifs.com", "gfycat.com"]
            # if entry['url'] in download_urls:
            #     log_msg = f"Duplicate,permalink:{entry['permalink']},url:{entry['url']}"
            #     duplicate_urls.put(log_msg)
            #     continue
            try:
                if any(domain in str(entry['url']) for domain in supported_domains_list):
                    entry_json_to_write = {
                        "author" : entry['author'],
                        "domain ": entry['domain'],
                        "post_id" : entry['id'],
                        "permalink" : entry['permalink'],
                        "subreddit_name" : entry['subreddit'],
                        "url": entry['url']
                    }
                    download_urls.append(entry['url'])
                    #download_entries.append(entry_json_to_write) # Starting a massive download queue
                    #file_entries.append(entry_json_to_write) # Will end up in the simplifie JSON file
                    file_entry_queue.put(entry_json_to_write)
                else:
                    json_skip_msg = f"Ignored,permalink:{entry['permalink']}, URL '{entry['domain']}' not in supported list"
                    json_skip_queue.put(json_skip_msg)
                for entry in download_entries:
                    futures.append(executor.submit(gallery_download, entry))
            except:
                print(f"Error processing file {file_name_to_process} - e")
        print(f" - Now Downloading...")
        with tqdm(total=len(futures)) as pbar:
            for future in concurrent.futures.as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    print(f"Error in process_file_entries: {e}")
                pbar.update(1)
        print(f"So far we have {file_entry_queue.qsize} items to download",flush=True)

def main():
    global downloaded_urls
    downloaded_urls = set()
    # Read in the list of subreddit names from the text file
    subreddit_file = 'subs'
    #json_folder = root_folder + "json/"
    json_folder = "/home/chadd/reddit/json"
    json_output_folder = root_folder + "json-output/"
    json_list = []
    global json_skip_queue
    json_skip_queue = Queue()
    if not os.path.exists(json_output_folder):
        os.makedirs(json_output_folder)
    global my_download_counter
    my_download_counter = 0
    #print(f"Loading entries from compressed JSON in {json_folder}...")
    print(f"Calling load_files")
    giant_ass_download_list = get_files(json_folder)
    print(f"Received {len(giant_ass_download_list)} entries to download")
    global download_entries
    global skipped_urls
    download_entries = []
    global download_urls
    download_urls = []
    global duplicate_urls
    global invalid_files
    invalid_files = Queue()

    # for filename in os.listdir(json_folder):
    #     if filename.endswith('_raw.json.gz'):
    #         print(f" - Processing {filename}")
    #         file_entries = [] # For storing the abbreviated JSON data for a given sub
    #         output_file_path = os.path.join(json_output_folder,filename)
    #         input_file_path = os.path.join(json_folder, filename)
    #         #print(f"Calculated {total_entries}")
    #         for entry in read_gzipped_json(input_file_path):
    #         #for entry in islice(read_gzipped_json(input_file_path), 100): #Limiting to 100 posts for testing
    #             # with open("entry_log", "a") as entry_log:
    #             #     entry_log.write(f"{entry['permalink']}\n")
    #             my_download_counter += 1
    #             # Gallery-dl only supports certain domains, and I'm only after the biggest ones
    #             # This will ensure only supported domains are processed
    #             # It will also help filter out a ton of the junk spam etc
    #             supported_domains_list = ["imgur.com", "redgifs.com", "gfycat.com"]
    #             if entry['url'] in download_urls:
    #                 log_msg = f"Duplicate,permalink:{entry['permalink']},url:{entry['url']}"
    #                 duplicate_urls.put(log_msg)
    #                 continue
    #             if any(domain in str(entry['url']) for domain in supported_domains_list):
    #                 entry_json_to_write = {
    #                     "author" : entry['author'],
    #                     "domain ": entry['domain'],
    #                     "post_id" : entry['id'],
    #                     "permalink" : entry['permalink'],
    #                     "subreddit_name" : entry['subreddit'],
    #                     "url": entry['url']
    #                 }
    #                 download_urls.append(entry['url'])
    #                 download_entries.append(entry_json_to_write) # Starting a massive download queue
    #                 file_entries.append(entry_json_to_write) # Will end up in the simplifie JSON file
    #             else:
    #                 json_skip_msg = f"Ignored,permalink:{entry['permalink']}, URL '{entry['domain']}' not in supported list"
    #                 json_skip_queue.put(json_skip_msg)

    #         # Write the simplified JSON to disk in case someone wants it later
    #         writer = GzippedJsonWriter(output_file_path)
    #         for entry in file_entries:
    #             writer.add_entry(entry)
    #         writer.finish()

    with concurrent.futures.ThreadPoolExecutor(max_workers=int(max_workers)) as executor:
        futures = []
        # for filename in os.listdir(json_folder):
        #     if filename.endswith('_raw.json.gz'):
        #         input_file_path = os.path.join(json_folder, filename)
        #         #futures.append(executor.submit(process_file_entries, input_file_path, root_folder))
        #         futures.append(executor.submit(process_file_entries, input_file_path))
        for entry in giant_ass_download_list:
            futures.append(executor.submit(gallery_download, entry))

        with tqdm(total=len(futures)) as pbar:
            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result()
                    # skipped_files.put(result["skipped"])
                    # json_skip_queue.put(result["ignored"])
                    # download_success.put(result["downloaded"])
                    # download_errors.put(result["errors"])
                    # duplicate_urls.put(result["duplicates"])
                except Exception as e:
                    print(f"Error in main.main: {e}")
                pbar.update(1) 

if __name__ == "__main__":
    global processed_files
    processed_files = set()
    start_time = time.time()
    # print("")
    # print("* IMPORTANT:")
    # print("************")
    # print("* If you want to cancel this you can't use 'ctrl+c'. ")
    # print("* You will need to use 'ctrl+z' and once it has stopped run 'kill %1'.")
    # print("")
    # print("Starting Process", flush=True)
    # print(" - Loading list of subreddits to scrape...", end='', flush=True)
    main()
    # print("")
    # print("Downloading Complete")
    # print(f"List of bad subs:" )
    # while not bad_subs.empty():
    #     item = bad_subs.get()
    #     print(f" - {item}")
    # print("")


    # # Delete the log file if it already exists
    # if os.path.exists(log_file):
    #     os.remove(log_file)

    skipCount = 0
    downloadCount = 0
    errorCount = 0
    ignoreCount = 0
    duplicateCount = 0
    rate_limit_count = 0
    global json_skip_queue
    skippedSet = set()
    ignoredSet = set()
    downloadSet = set()
    errorSet = set()
    duplicateSet = set()

    while not skipped_files.empty():
        item = skipped_files.get().strip()
        skippedSet.add(item)

    while not json_skip_queue.empty():
        item = json_skip_queue.get().strip()
        ignoredSet.add(item)
    
    while not download_success.empty():
        item = download_success.get().strip()
        downloadSet.add(item)

    while not download_errors.empty():
            item = download_errors.get().strip()
            errorSet.add(item)
    
    while not duplicate_urls.empty():
            item = duplicate_urls.get().strip()
            duplicateSet.add(item)




    log_file = "output_log.txt"
    with open(log_file, "w") as log:
        log.write("List of files we skipped (Already existed):\n")
        # while not skipped_files.empty():
        #     item = skipped_files.get().strip()
        #     log.write(f" - {item}\n")
        #     skipCount += 1
        for line in skippedSet:
            log.write(f" - {line}\n")
            skipCount += 1
        
        log.write("\nList of ignored posts (unsupported domain):\n")
        # while not json_skip_queue.empty():
        #     item = json_skip_queue.get().strip()
        #     ignoredSet.add(item)
        #     log.write(f" - {item}\n")
        #     ignoreCount += 1
        for line in ignoredSet:
            log.write(f" - {line}\n")
            ignoreCount +=1

        log.write("\nList of files downloaded:\n")
        # while not download_success.empty():
        #     item = download_success.get().strip()
        #     if item not in processed_files:
        #         log.write(f" - {item}\n")
        #         downloadCount += 1
        for line in downloadSet:
            log.write(f" - {line}\n")
            downloadCount += 1

        log.write("\nList of URLs we failed to retrieve:\n")
        # while not download_errors.empty():
        #     item = download_errors.get().strip()
        #     log.write(f" - Unable to download: {item}\n")
        #     errorCount += 1
        for line in errorSet:
            log.write(f" - {line}\n")
            errorCount += 1

        log.write("\nList of Duplicate URLs in the original data:\n")
        # while not duplicate_urls.empty():
        #     item = duplicate_urls.get().strip()
        #     log.write(f" - {item}\n")
        #     duplicateCount += 1
        for line in duplicateSet:
            log.write(f" - {line}\n")
            duplicateCount += 1

        log.write("\nList of URLs that were rate limited")
        while not rate_limit_queue.empty():
            item = rate_limit_queue.get().strip()
            log.write(f"rate_limit,{item}\n")
            rate_limit_count += 1

    print(f"\nAll done!")
    print(f"\nLogs can be found in {log_file}")
    print(f"Media is in {root_folder}subreddits")
    print(f"Original JSON is in {root_folder}json")
    print(f"Simplified JSON (in case you want to rename or organize) is in {root_folder}json-output")
    print(f"")

    end_time = time.time()
    total_time = end_time - start_time
    total_minutes = round(total_time / 60)
    global download_entries
    total_urls = len(download_entries)
    if total_time < 120:
        print(f"Overall, I processed {my_download_counter} files in {int(total_time)} seconds")
    elif total_minutes < 120:
        print(f"Overall, I processed {my_download_counter} files in {total_minutes} minutes")
    else:
        total_hours = round(total_time / 3600, 1)
        print(f"Overall, I processed {my_download_counter} files in {total_hours} hours")

    print(f" - {skipCount} files were skipped (already exist)")
    print(f" - {ignoreCount} were ignored (unsupported or spam)")
    print(f" - {downloadCount} files were downloaded")
    print(f" - {errorCount} files had errors")
    print(f" - {duplicateCount} URLs were duplicates in the original data")
    if rate_limit_count > 5:
        print(f" - {rate_limit_count} URLS failed due to rate-limiting")
        print(f"    You may want to consider slowing things down")
        print(f"    Or at least retrying the failed ones")
        print(f"    See {log_file} for details")
    totalCount = skipCount + ignoreCount + downloadCount + errorCount + duplicateCount
    print(f"QA Check: Started with {my_download_counter} entries and accounted for {totalCount} of them.")



