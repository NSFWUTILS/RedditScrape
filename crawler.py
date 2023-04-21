import os
import configparser
import praw
from utils import checkMime, download_video_from_text_file
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
global processed_urls
global total_urls
global download_queue
global download_counter
download_counter = 0
processed_urls = 0
total_urls = 1
download_success = Queue()
download_errors = Queue()
bad_subs = Queue()
skipped_files = Queue()
download_queue = Queue()
# Set up the root filesystem folder
root_folder = config["CONFIG"]["MEDIA_FOLDER"]


def create_custom_session(pool_size, pool_block=True):
    session = Session()
    adapter = HTTPAdapter(pool_connections=pool_size, pool_maxsize=pool_size, pool_block=pool_block)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session

# Set up the Reddit API client
praw_session = create_custom_session(36, pool_block=False)
reddit = praw.Reddit(client_id=client_id, client_secret=client_secret, user_agent=client_user_agent, requestor_kwargs={'session': praw_session})

def update_progress():
    #print(f"Total URL Count: {total_urls}",flush=True)
    # while not download_queue.empty():
    #     download_counter += 1
        #progress = (processed_urls / total_urls) * 100
    download_counter = download_queue.qsize()
    progress = (download_counter / total_urls ) * 100
    print(f"\rProgress: {progress:.2f}%",end="", flush=True)


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
            processed_urls += 1
            update_progress()
            #print(f"File downloaded: {file_path}")
    else:
        #print(f"Error downloading {url} - status code {response.status_code}")
        download_errors.put(url)



def process_post(post, subreddit_folder, session):
    #print(f"Processing post: {post.url}")
    file_name = os.path.basename(post.url)
    file_path = os.path.join(subreddit_folder, file_name)
    # if os.path.exists(file_path):
    #     print(f"Skipping {file_path}")
    #     return
    gallery_command = f'python -m gallery_dl -D {subreddit_folder} "{post.url}" '
    try:
        if "redgifs.com" in post.url or "gfycat.com" in post.url:
            if os.path.exists(file_path):
                skipped_files.put(file_path)
                return
            result = subprocess.run(gallery_command, shell=True, text=True, capture_output=True)
            if result:
                if result.stdout != "" and "#" not in result.stdout:
                    download_success.put(result.stdout)
                    download_queue.put(file_path)
                    update_progress()
        else:
            download_file(post.url, file_path, session)
            download_queue.put(file_path)
            update_progress()

    except Exception as e:
        error_message = "Error processing URL: " + post.url + " - " + e
        download_errors.put(error_message)


def process_subreddit(subreddit_name, downloaded_urls, session):
    global total_urls
    subreddit_folder = os.path.join(root_folder, subreddit_name)
    os.makedirs(subreddit_folder, exist_ok=True)

    subreddit = reddit.subreddit(subreddit_name)
    try:
        subreddit.id


    except:
        bad_subs.put(subreddit_name)
        return

    # Create a regular list of posts
    post_method = getattr(subreddit, sort_type)
    posts = list(post_method(time_filter=time_period, limit=int(post_limit)))
    with concurrent.futures.ThreadPoolExecutor(max_workers=int(maxWorkers)) as executor:
        #session = create_custom_session(40)
        for post in posts:
            if post.url not in downloaded_urls:
                try:
                    total_urls += 1
                    executor.submit(process_post, post, subreddit_folder, session)
                    downloaded_urls.add(post.url)
                    #print(f"Adding {post.url} to task list")
                except Exception as e:
                    print(f"Error processing url: {post.url} - {e}")



def main():
    downloaded_urls = set()
    # Read in the list of subreddit names from the text file
    subreddit_file = 'subs'
    with open(subreddit_file) as f:
        subreddit_names = f.read().splitlines()

    with concurrent.futures.ThreadPoolExecutor() as executor:
        session = create_custom_session(int(poolSize))
        futures = []
        print("done", flush=True)
        print(f"Gathering list of topics and files to download (the real work begins)...", flush=True)
        for subreddit_name in subreddit_names:
            futures.append(executor.submit(process_subreddit, subreddit_name, downloaded_urls, session))

        for future in concurrent.futures.as_completed(futures):
            try:
                future.result()
                time.sleep(1)
            except Exception as e:
                print(f"Error in process_subreddit: {e}")

if __name__ == "__main__":
    start_time = time.time()
    print("")
    print("* IMPORTANT:")
    print("************")
    print("* If you want to cancel this you can't use 'ctrl+c'. ")
    print("* You will need to use 'ctrl+z' and once it has stopped run 'kill %1'.")
    print("")
    print("Starting Process", flush=True)
    print("")
    print("Loading list of subreddits to scrape...", end='', flush=True)
    main()
    print("")
    print("Downloading Complete")
    print(f"List of bad subs:" )
    while not bad_subs.empty():
        item = bad_subs.get()
        print(f" - {item}")
    print("")

    log_file = "output_log.txt"

    # Delete the log file if it already exists
    if os.path.exists(log_file):
        os.remove(log_file)

    skipCount = 0
    downloadCount = 0
    errorCount = 0

    with open(log_file, "w") as log:
        log.write("List of files we skipped (Already existed):\n")
        while not skipped_files.empty():
            item = skipped_files.get()
            log.write(f" - {item}\n")
            skipCount += 1

        log.write("\nList of files downloaded:\n")
        while not download_success.empty():
            item = download_success.get().strip()
            log.write(f" - {item}\n")
            downloadCount += 1

        log.write("\nList of URLs we failed to retrieve:\n")
        while not download_errors.empty():
            item = download_errors.get()
            log.write(f" - Unable to download: {item}\n")
            errorCount += 1

    print(f"All done. Logs can be found in {log_file}")
    print(f"Media is in {root_folder}")
    print(f"")

    end_time = time.time()
    total_time = end_time - start_time
    total_minutes = round(total_time / 60)

    if total_minutes < 120:
        print(f"Overall, I processed {total_urls} files in {total_minutes} minutes")
    else:
        total_hours = round(total_time / 3600, 1)
        print(f"Overall, I processed {total_urls} files in {total_hours} hours")

    print(f" - {skipCount} files were skipped")
    print(f" - {downloadCount} files were downloaded")
    print(f" - {errorCount} files had errors")
    print(f"I have no idea what happened to the other {total_urls - skipCount - downloadCount - errorCount} files...")


