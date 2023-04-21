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
from requests.adapters import HTTPAdapter
from requests.sessions import Session
import subprocess



# Setup the configparser to read the config file named 'config'
config = configparser.ConfigParser()
config.read("config")
client_id = config["CONFIG"]["REDDIT_CLIENT_ID"]
client_secret = config["CONFIG"]["REDDIT_CLIENT_SECRET"]
client_user_agent = config["CONFIG"]["REDDIT_USER_AGENT"]
post_limit = config["CONFIG"]["REDDIT_POST_LIMIT"]
sort_type = config["CONFIG"]["REDDIT_SORT_METHOD"]
time_period = config["CONFIG"]["REDDIT_TIME_PERIOD"]
maxWorkers = config["CONFIG"]["MAX_WORKERS"]
poolSize = config["CONFIG"]["POOL_SIZE"]



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



# def download_file(url, file_path):
#     #response = requests.get(url)
#     response = session.get(url)
#     if response.status_code == 200:
#         with open(file_path, 'wb') as f:
#             f.write(response.content)
#             download_success.append(file_path)
#     else:
#         print(f"Error downloading {url} - status code {response.status_code}")
#         download_errors.append(url)

def create_custom_session(pool_size, pool_block=True):
    session = Session()
    adapter = HTTPAdapter(pool_connections=pool_size, pool_maxsize=pool_size, pool_block=pool_block)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

# Set up the Reddit API client
praw_session = create_custom_session(36, pool_block=False)
reddit = praw.Reddit(client_id=client_id, client_secret=client_secret, user_agent=client_user_agent, requestor_kwargs={'session': praw_session})
#reddit = praw.Reddit(client_id=client_id, client_secret=client_secret, user_agent=client_user_agent)


#def download_file(url, file_path):
def download_file(url, file_path, session):
    #print(f"Attempting to download {url} to {file_path}", flush=True)
    if os.path.exists(file_path):
        skipped_files.put(file_path)
        return

    #response = requests.get(url)
    response = session.get(url)
    if response.status_code == 200:
        with open(file_path, 'wb') as f:
            f.write(response.content)
            download_success.put(file_path)
            #print(f"File downloaded: {file_path}")
    else:
        print(f"Error downloading {url} - status code {response.status_code}")
        download_errors.put(url)



#def process_post(post, subreddit_folder):
def process_post(post, subreddit_folder, session):
    #print(f"Processing post: {post.url}")
    file_name = os.path.basename(post.url)
    file_path = os.path.join(subreddit_folder, file_name)
    # if os.path.exists(file_path):
    #     return
    gallery_command = f'python -m gallery_dl -D {subreddit_folder} "{post.url}" '
    try:
        if "redgifs.com" in post.url or "gfycat.com" in post.url:
            if os.path.exists(file_path):
                skipped_files.put(file_path)
                return
            #print(f"redgif call to download {post.url} and file path: {file_path}")
            #os.system(gallery_command)
            result = subprocess.run(gallery_command, shell=True, text=True, capture_output=True)
            if result:
                if result.stdout != "" and "#" not in result.stdout:
                    download_success.put(result.stdout)
        else:
#            print(f"Making call to download_file for {post.url} and file path: {file_path}")
            #print(f"Using gallery to download {file_path}")
            #download_file(post.url, file_path)
            download_file(post.url, file_path, session)
            #os.system(gallery_command)

#        store_post_metadata(post, file_name)
    except Exception as e:
        print(f"Error processing url: {post.url} - {e}")

def process_subreddit(subreddit_name, downloaded_urls, session):
    subreddit_folder = os.path.join(root_folder, subreddit_name)
    os.makedirs(subreddit_folder, exist_ok=True)

    subreddit = reddit.subreddit(subreddit_name)
    try:
        subreddit.id
        #print(f"### Processing Sub {subreddit_name}")


    except:
        #print(f"### Sub {subreddit_name} doesn't exist")
        bad_subs.put(subreddit_name)
        return

    # Create a regular list of posts
    post_method = getattr(subreddit, sort_type)
    posts = list(post_method(time_filter=time_period, limit=int(post_limit)))

    #with concurrent.futures.ThreadPoolExecutor() as executor:
    with concurrent.futures.ThreadPoolExecutor(max_workers=int(maxWorkers)) as executor:
        #session = create_custom_session(40)
        for post in posts:
            if post.url not in downloaded_urls:
                try:
#                    executor.submit(process_post, post, subreddit_folder)
                    executor.submit(process_post, post, subreddit_folder, session)
                    downloaded_urls.add(post.url)
                    #print(f"Adding {post.url} to task list")
                except Exception as e:
                    print(f"Error processing url: {post.url} - {e}")

# def main():
#     print("Starting Process", flush=True)
#     downloaded_urls = set()

#     # Read in the list of subreddit names from the text file
#     subreddit_file = 'subs'
#     with open(subreddit_file) as f:
#         subreddit_names = f.read().splitlines()

#     with concurrent.futures.ThreadPoolExecutor() as executor:
#         futures = []
#         for subreddit_name in subreddit_names:
#             futures.append(executor.submit(process_subreddit, subreddit_name, downloaded_urls))

#         for future in concurrent.futures.as_completed(futures):
#             try:
#                 future.result()
#                 time.sleep(1)
#             except Exception as e:
#                 print(f"Error in process_subreddit: {e}")

def main():
    print("Starting Process", flush=True)
    print("Loading list of subreddits to scrape...", end='', flush=True)
    downloaded_urls = set()

    # Create a custom session with an increased connection pool size
#    session = create_custom_session(40)

    # Read in the list of subreddit names from the text file
    subreddit_file = 'subs'
    with open(subreddit_file) as f:
        subreddit_names = f.read().splitlines()

    with concurrent.futures.ThreadPoolExecutor() as executor:
        session = create_custom_session(int(poolSize))
        futures = []
        for subreddit_name in subreddit_names:
            futures.append(executor.submit(process_subreddit, subreddit_name, downloaded_urls, session))

        for future in concurrent.futures.as_completed(futures):
            try:
                future.result()
                time.sleep(1)
            except Exception as e:
                print(f"Error in process_subreddit: {e}")
    print("done", flush=True)




if __name__ == "__main__":
    main()
    print(f"List of bad subs:" )
    while not bad_subs.empty():
        item = bad_subs.get()
        print(f" - {item}")
    print("")
    # print("List of files we skipped (Already existed):")
    # while not skipped_files.empty():
    #     item = skipped_files.get()
    #     print(f" - {item}")
    # print("List of files downloaded:")
    # while not download_success.empty():
    #     item = download_success.get().strip()
    #     print(f" - {item}", flush=True)
    # print("")
    # print("List of URLs we failed to retrieve:")
    # while not download_errors.empty():
    #     item = download_errors.get()
    #     print(f" - Unable to download: {item}", flush=True)
    log_file = "output_log.txt"

    # Delete the log file if it already exists
    if os.path.exists(log_file):
        os.remove(log_file)

    with open(log_file, "w") as log:
        log.write("List of files we skipped (Already existed):\n")
        while not skipped_files.empty():
            item = skipped_files.get()
            log.write(f" - {item}\n")

        log.write("\nList of files downloaded:\n")
        while not download_success.empty():
            item = download_success.get().strip()
            log.write(f" - {item}\n")

        log.write("\nList of URLs we failed to retrieve:\n")
        while not download_errors.empty():
            item = download_errors.get()
            log.write(f" - Unable to download: {item}\n")

    print(f"All done. Logs can be found in {log_file}")
    print(f"Media is in {root_folder}")
    print(f"")


