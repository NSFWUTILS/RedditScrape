import os
import sys
import time
import concurrent.futures
from queue import Queue
from requests.adapters import HTTPAdapter
from requests.sessions import Session
import subprocess
import configparser
import praw
from utils import download_video_from_text_file
from utils import clean_title
import pdb


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
global root_folder
global sub_mode
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
    response = session.get(url)
    if response.status_code==404:
        print(f"404: {url}")

    #If a successful response with image content type...
    elif response.status_code==200 and 'image' in response.headers['content-type']:
        #If it's a decent sized, it's probably legit; grab it.
        if len(response.content)>16*1024:
            with open(file_path, 'wb') as f:
                global processed_urls
                f.write(response.content)
                download_success.put(file_path)
                processed_urls += 1
                update_progress()
                #print(f"File downloaded: {file_path}")
        
        #If it's tiny, it's probably a "not found" image from the host; skip it.
        else:
            print(f"Image probably removed from host: {url}")
    
    #If it's text, see if there's a image link within it and try to grab that.
    elif 'text' in response.headers['content-type']:
        with open(file_path, 'wb') as f:
            f.write(response.content)
        if download_video_from_text_file(file_path):
            download_success.put(file_path)
            processed_urls += 1
            update_progress()
        os.remove(file_path)

    else:
        #print(f"Error downloading {url}:\nStatus {response.status_code}\n{response.headers}")
        download_errors.put(url)

def gallery_download(subreddit_folder, post):
    reddit_url = "https://www.reddit.com" + post.permalink
    post_title = clean_title(post.title)
    #print(f"Reddit URL: {reddit_url}",flush=True)
    #print(f"Post Permalink: {post.permalink}",flush=True)
    #gallery_command = f'python -m gallery_dl -D {subreddit_folder} -f "{post_title}.{extension} "{post.url}" '
    gallery_command = f'python -m gallery_dl -D {subreddit_folder} -f "{post_title}.{{extension}}" {reddit_url} '
    #print(f"Running gallery: {gallery_command}",flush=True)
    result = subprocess.run(gallery_command, shell=True, text=True, capture_output=True)
    #print(f"Result STDOUT: {result.stdout}",flush=True)
    #print(f"Result STDERR: {result.stderr}",flush=True)
    #if "#" in result.stdout:
        #print(f"Skipping: {post_title}",flush=True)
        #skipped_files.put(post_title)
    return result.stdout



def process_post(post, subreddit_folder, session):
    #print(f"Processing post: {post.url}")
    file_name = os.path.basename(post.url)
    file_path = os.path.join(subreddit_folder, file_name)
    try:
        #print(f"Trying to download {file_path}",flush=True)
        result = gallery_download(subreddit_folder,post)
        #print(f"Result: {result}",flush=True)
        if "#" in result:
            skipped_files.put(result)
            #print(f"Skipping {file_path}",flush=True)
            update_progress()
        else:
            download_success.put(result)
            download_queue.put(result)
            update_progress()
            #print(f"Downloaded {result}",flush=True)

    except Exception as e:
        error_message = "Error processing URL: " + post.url + " - " + e
        download_errors.put(error_message)


def process_subreddit(subreddit_name, downloaded_urls, session):
    global total_urls
    global sub_mode
    subreddit_folder = os.path.join(root_folder, subreddit_name)
    os.makedirs(subreddit_folder, exist_ok=True)

    if sub_mode=='user_file':
        subreddit = reddit.redditor(subreddit_name)
    else:
        subreddit = reddit.subreddit(subreddit_name)
    
    if not hasattr(subreddit,'id'):
        bad_subs.put(subreddit_name)
        return

    # Create a regular list of posts
    post_method = getattr(subreddit, sort_type)
    if sort_type == "top" or sort_type == "controversial":
        posts = list(post_method(time_filter=time_period, limit=int(post_limit)))
    else:
        posts = list(post_method(limit=int(post_limit)))
    with concurrent.futures.ThreadPoolExecutor(max_workers=int(maxWorkers)) as executor:
        #session = create_custom_session(40)
        for post in posts:
            if not hasattr(post,'url'):
                continue
            # print(f"Post Title: {post.title}", flush=True)
            # print(f" - Clean  : {clean_title(post.title)}")
            # print("")
            if post.url not in downloaded_urls:
                try:
                    total_urls += 1
                    executor.submit(process_post, post, subreddit_folder, session)
                    downloaded_urls.add(post.url)
                    #print(f"Adding {post.url} to task list")
                except Exception as e:
                    print(f"Error processing url: {post.url} - {e}")

def main():
    """ """
    global root_folder
    global sub_mode
    downloaded_urls = set()
    
    #By default, use the subs list.
    if len(sys.argv)<=1 or sys.argv[1]=='subs_file':
        sub_mode='subs_file' 
        subreddit_names=open('subs').read().splitlines()
    elif sys.argv[1]=='users_file':
        sub_mode='user_file' 
        subreddit_names=open('users').read().splitlines()
        root_folder+="\_users"
    else:
        print("Invalid operating mode")
        sys.exit()
    
    
    
    with concurrent.futures.ThreadPoolExecutor() as executor:
        session = create_custom_session(int(poolSize))
        futures = []
        print("done", flush=True)
        print(" - Gathering list of topics and files to download...", flush=True)
        for subreddit_name in subreddit_names:
            futures.append(executor.submit(process_subreddit, subreddit_name, downloaded_urls, session))
        print(" - Now Downloading...")
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
    print(" - Loading list of subreddits to scrape...", end='', flush=True)
    main()
    print("")
    print("Downloading Complete")
    print("List of bad subs:" )
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
            item = skipped_files.get().strip()
            log.write(f" - {item}\n")
            skipCount += 1

        log.write("\nList of files downloaded:\n")
        while not download_success.empty():
            item = download_success.get().strip()
            log.write(f" - {item}\n")
            downloadCount += 1
            # I forgot to check for text files (logs of .gifv are text/html)
            # print("Checking for sneaking gifv text files")
            # if checkMime(item):
            #     print(f"Found a text file: {item}")
            #     print(f" - Retrieving proper video from {item}")
            #     download_video_from_text_file(item)

        log.write("\nList of URLs we failed to retrieve:\n")
        while not download_errors.empty():
            item = download_errors.get()
            log.write(f" - Unable to download: {item}\n")
            errorCount += 1

    print(f"All done. Logs can be found in {log_file}")
    print(f"Media is in {root_folder}")
    print("")

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


