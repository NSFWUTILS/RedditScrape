import os
import csv
import configparser
import praw
from utils import checkMime, download_video_from_text_file
from redgifdl import download
import concurrent.futures
import requests
import time
from queue import Queue


# Setup the configparser to read the config file named 'config'
config = configparser.ConfigParser()
config.read("config")
client_id = config["CONFIG"]["REDDIT_CLIENT_ID"]
client_secret = config["CONFIG"]["REDDIT_CLIENT_SECRET"]
client_user_agent = config["CONFIG"]["REDDIT_USER_AGENT"]
post_limit = config["CONFIG"]["REDDIT_POST_LIMIT"]
sort_type = config["CONFIG"]["REDDIT_SORT_METHOD"]
time_period = config["CONFIG"]["REDDIT_TIME_PERIOD"]



global bad_subs
global download_errors
global download_success
global skipped_files
download_success = Queue()
download_errors = Queue()
bad_subs = Queue()
skipped_files = Queue()
# Set up the root filesystem folder
root_folder = config["CONFIG"]["MEDIA_FOLDER"]

# Set up the Reddit API client
reddit = praw.Reddit(client_id=client_id, client_secret=client_secret, user_agent='YataGPT')

# def download_file(url, file_path):
#     response = requests.get(url)
#     if response.status_code == 200:
#         with open(file_path, 'wb') as f:
#             f.write(response.content)
#             download_success.append(file_path)
#     else:
#         print(f"Error downloading {url} - status code {response.status_code}")
#         download_errors.append(url)

def download_file(url, file_path):
    #print(f"Attempting to download {url} to {file_path}", flush=True)
    if os.path.exists(file_path):
        skipped_files.put(file_path)
        return

    response = requests.get(url)
    if response.status_code == 200:
        with open(file_path, 'wb') as f:
            f.write(response.content)
            download_success.put(file_path)
            print(f"File downloaded: {file_path}")
    else:
        print(f"Error downloading {url} - status code {response.status_code}")
        download_errors.put(url)



def process_post(post, subreddit_folder):
    #print(f"Processing post: {post.url}")
    file_name = os.path.basename(post.url)
    file_path = os.path.join(subreddit_folder, file_name)
    # if os.path.exists(file_path):
    #     return
    gallery_command = f'python -m gallery_dl -D {subreddit_folder} "{post.url}" > /dev/null'
    try:
        if "redgifs.com" in post.url or "gfycat.com" in post.url:
            #print(f"redgif call to download {post.url} and file path: {file_path}")
            os.system(gallery_command)
            download_success.put(file_path)
        else:
#            print(f"Making call to download_file for {post.url} and file path: {file_path}")
            print(f"Using gallery to download {file_path}")
            #download_file(post.url, file_path)
            os.system(gallery_command)

#        store_post_metadata(post, file_name)
    except Exception as e:
        print(f"Error processing url: {post.url} - {e}")

def process_subreddit(subreddit_name, downloaded_urls):
    subreddit_folder = os.path.join(root_folder, subreddit_name)
    os.makedirs(subreddit_folder, exist_ok=True)

    subreddit = reddit.subreddit(subreddit_name)
    try:
        subreddit.id
        print(f"### Processing Sub {subreddit_name}")
    except:
        print(f"### Sub {subreddit_name} doesn't exist")
        bad_subs.put(subreddit_name)
        return

    # Create a regular list of posts
    post_method = getattr(subreddit, sort_type)
    posts = list(post_method(time_filter=time_period, limit=int(post_limit)))

    #with concurrent.futures.ThreadPoolExecutor() as executor:
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:

        for post in posts:
            if post.url not in downloaded_urls:
                try:
                    executor.submit(process_post, post, subreddit_folder)
                    downloaded_urls.add(post.url)
                    #print(f"Adding {post.url} to task list")
                except Exception as e:
                    print(f"Error processing url: {post.url} - {e}")

def main():
    print("Starting Process", flush=True)
    downloaded_urls = set()

    # Read in the list of subreddit names from the text file
    subreddit_file = 'subs'
    with open(subreddit_file) as f:
        subreddit_names = f.read().splitlines()

    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = []
        for subreddit_name in subreddit_names:
            futures.append(executor.submit(process_subreddit, subreddit_name, downloaded_urls))

        for future in concurrent.futures.as_completed(futures):
            try:
                future.result()
                sleep(1)
            except Exception as e:
                print(f"Error in process_subreddit: {e}")




if __name__ == "__main__":
    main()
    print(f"List of bad subs:" )
    while not bad_subs.empty():
        item = bad_subs.get()
        print(f" - {item}")
    print("")
    print("List of files we skipped (Already existed):")
    while not skipped_files.empty():
        item = skipped_files.get()
        print(f" - {item}")
    print("List of files downloaded:")
    while not download_success.empty():
        item = download_success.get()
        print(f" - {item}", flush=True)
    print("")
    print("List of URLs we failed to retrieve:")
    while not download_errors.empty():
        item = download_errors.get()
        print(f" - Unable to download: {item}", flush=True)

