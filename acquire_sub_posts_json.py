import requests
import urllib.parse
from datetime import datetime
import json
import gzip
import os
import shutil
import signal
from contextlib import contextmanager
import time
import argparse
import configparser
import concurrent.futures
from contextlib import contextmanager


config = configparser.ConfigParser()
config.read("config")
maxWorkers = int(config["CONFIG"]["MAX_WORKERS"])
poolSize = int(config["CONFIG"]["POOL_SIZE"])
root_folder = config["CONFIG"]["MEDIA_FOLDER"]
global interrupted
interrupted = False

class NoQuotedCommasSession(requests.Session):
    """
    A custom session class that inherits from requests.Session and overrides the send method
    to avoid URL encoding of commas and allows setting a custom timeout.
    """
    def __init__(self, timeout=None):
        super().__init__()
        self.timeout = timeout
    
    def send(self, *a, **kw):
        a[0].url = a[0].url.replace(urllib.parse.quote(','), ',')
        if self.timeout is not None:
            kw['timeout'] = self.timeout
        return super().send(*a, **kw)

class GracefulInterrupt(Exception):
    """
    A custom exception class to handle graceful interruption of the script.
    """
    pass

#@contextmanager
class handle_interrupt:
    def __init__(self, func):
        self.func = func

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        global interrupted
        if exc_type == KeyboardInterrupt:
            interrupted = True
            print("Interrupt requested. Waiting for tasks to finish...")
            time.sleep(1)
            return True
        return False

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)






def fetch_chunk(sub_name, after=None, before=None, max_retries=7, retry_delay=5):
    """
    Fetch a chunk of subreddit posts from the Pushshift API.
    
    Args:
        sub_name (str): The name of the subreddit to fetch posts from.
        after (int, optional): The timestamp to fetch posts after.
        max_retries (int, optional): The maximum number of retries before giving up.
        retry_delay (int, optional): The delay between retries in seconds.
    
    Returns:
        list: A list of post dictionaries fetched from the API.
    """
    params = {
        'subreddit': sub_name,
        'fields': 'id,created_utc,domain,author,title,selftext,permalink',
        'sort': 'created_utc',
        'order': 'asc',
        'size': 1000,
    }
    if after is not None:
        params['after'] = after
    if before is not None:
        params['before'] = before
    
    retries = 0
    while retries <= max_retries:
        try:
            resp = NoQuotedCommasSession().get('https://api.pushshift.io/reddit/submission/search', params=params)
            resp.raise_for_status()
            return resp.json()['data']
        except requests.HTTPError as e:
            if e.response.status_code == 524:
                print(f"Server timeout. Retrying in {retry_delay} seconds... (attempt {retries + 1}/{max_retries})")
                retries += 1
                time.sleep(retry_delay)
            else:
                raise
    raise RuntimeError("Max retries exceeded. Aborting.")

def fetch_all_subreddit_posts(sub_name, after=None, before=None):
    """
    Fetch all subreddit posts using the Pushshift API, in chunks.
    
    Args:
        sub_name (str): The name of the subreddit to fetch posts from.
        after (int, optional): The timestamp to fetch posts after.
        before (int, optional): The timestamp to fetch posts before.
    
    Yields:
        dict: A dictionary containing post data.
    """
    global interrupted
    global total_num_subs
    global sub_counter
    if interrupted:
        print("Interrupted by user. Aborting.")
        return
    sub_counter += 1
    i = 1
    while True:
        print(f'loading chunk {i}')
        chunk = fetch_chunk(sub_name, after, before)
        if not chunk:
            break
        yield from chunk
        after = chunk[-1]['created_utc'] + 1
        if i % 5 == 0:
            print(f'{sub_name} loaded until {datetime.fromtimestamp(after)}')
            print(f" - On {sub_counter} of {total_num_subs} subreddits")
        i += 1
    print(f'done! loaded until {datetime.fromtimestamp(after)}')

def compress_and_delete_json(input_file_path):
    """
    Compress a JSON file using gzip and delete the original file.
    
    This function reads the input JSON file, compresses it using gzip,
    and saves the compressed content to a new file. It then deletes the
    original JSON file.
    
    Args:
        input_file_path (str): The path to the input JSON file.
    
    Example usage:
        compress_and_delete_json('subreddit_posts.json')
    """
    output_file_path = input_file_path + '.gz'
    
    with open(input_file_path, 'rb') as input_file:
        with gzip.open(output_file_path, 'wb') as output_file:
            shutil.copyfileobj(input_file, output_file)
    
    os.remove(input_file_path)

def write_posts_to_file(file_path, sub_name, is_incomplete=False, after=None, before=None):
    """
    Write the posts yielded by the post_generator to a compressed JSON file.
    
    This function writes each post in the post_generator to the specified
    compressed JSON file. The posts are written as a JSON array, with each post
    separated by a comma and a newline.
    
    Args:
        file_path (str): The path to the compressed file to save the posts.
        sub_name (str): The name of the subreddit to fetch posts from.
        is_incomplete (bool, optional): Whether the file is incomplete.
        after (int, optional): The timestamp to fetch posts after.
    
    Example usage:
        write_posts_to_file('subreddit_posts.json.gz', 'eyebleach')
    """
    global interrupted
    global total_num_subs
    global sub_counter
    filename = os.path.basename(file_path)
    if not os.path.isfile(file_path):
        # Create file so we can open it in 'rb+' mode
        f = open(file_path, 'w')
        f.close()
    # Files are written uncompressed initially, so we can seek to the end when necessary
    with open(file_path, 'rb+') as f:
        post_generator = fetch_all_subreddit_posts(sub_name, after, before)
        if not is_incomplete:
            f.write(b'[')
            first_post = True
        else:
            first_post = False
            f.seek(0, os.SEEK_END)
            current_position = f.tell()
            while current_position > 0:
                current_position -= 1
                f.seek(current_position)
                current_char = f.read(1)
                if current_char == b'}':
                    current_position += 1
                    f.seek(current_position)
                    break
        
        save_incomplete = False
        delete_incomplete = False
        file_finished = False
        post = None
        try:
            #with handle_graceful_interrupt():
            for post in post_generator:
                if interrupted:
                    break
                if not first_post:
                    f.write(b',\n')
                else:
                    first_post = False
                json_string = json.dumps(post)
                json_bytes = json_string.encode('utf-8')
                f.write(json_bytes)
            f.write(b'\n]')
            file_finished = True
        except requests.HTTPError as e:
            if e.response.status_code == 524:
                print("Server timeout.")
            else:
                print(f"Unexpected server error: {e.response.status_code}")
            
            if first_post:
                delete_incomplete = True
            else:
                save_incomplete = True
        except KeyboardInterrupt:
            print("Interrupted by user. Finishing up the file.")
            save_incomplete = True
        except Exception as e:
            print(f"Unexpected error: {e}")
            interrupted = True
            if first_post:
                delete_incomplete = True
            else:
                save_incomplete = True
        
        if save_incomplete:
            print(f"Saving incomplete file: \"{filename}\"")
            f.write(b'\n]')
            if post is not None:
                timestamp = post["created_utc"]
                return timestamp
            else:
                return after
    
    if delete_incomplete:
        print("No file saved")
        os.remove(file_path)
        return None
    
    if file_finished:
        # Compression time
        compress_and_delete_json(file_path)
        print(f"File {filename} finished and compressed")
    
    return None



def dump_subreddit_json(sub_name, out_dir='./', stop_early=False):
    """
    Dump subreddit posts into a JSON file.

    This function checks if the JSON file with subreddit posts exists, and if it is complete or
    incomplete. If it is incomplete, the function resumes the data collection from the last known
    timestamp. If the file doesn't exist, the function starts collecting data from the beginning.
    The collected data is saved to a JSON file, and if the process is interrupted, an
    '.incomplete' file is created to store the last post's timestamp.

    Args:
        sub_name (str): The name of the subreddit to fetch posts from.
    """
    out_dir = root_folder + "json/"
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)
    filename = f'{sub_name}_subreddit_posts_raw.json'
    file_path = os.path.join(out_dir, filename)
    incomplete_path = file_path + '.incomplete'
    is_incomplete = os.path.isfile(incomplete_path)
    file_exists = os.path.isfile(file_path)
    print(f"Storing JSON in {file_path}")

    if os.path.isfile(file_path + ".gz"):
        print(f"Zipped version of file already exists: {filename}.gz\nTo generate a new one, \
manually delete it and rerun the script.")
        return

    if is_incomplete and not file_exists:
        os.remove(incomplete_path)
        is_incomplete = False

    if file_exists and not is_incomplete:
        print(f"Error. File \"{filename}\" exists and does not seem to be incomplete. If it is \
incomplete, create a new '.incomplete' file with the last post's timestamp. If it is completely \
broken, delete it. Then, rerun the script. Otherwise, manually zip it with gzip.")
        return

    before = None
    if stop_early:
        before = 1577862000 # Jan 1, 2020: Onlyfans surges in popularity
    if is_incomplete:
        with open(incomplete_path, 'r') as incomplete_file:
            timestamp_s = incomplete_file.readline()
            timestamp = int(timestamp_s)

        with open(incomplete_path, 'w') as incomplete_file:
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
                result = executor.submit(write_posts_to_file, file_path, sub_name, is_incomplete=True, after=timestamp, before=before).result()
                if result is not None:
                    incomplete_file.write(str(result))

        if result is None:
            os.remove(incomplete_path)
    else:
        result = None
        with open(incomplete_path, 'w') as incomplete_file:
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
                result = executor.submit(write_posts_to_file, file_path, sub_name, before=before).result()
                if result is not None:
                    incomplete_file.write(str(result))

        if result is None:
            os.remove(incomplete_path)


def main_func(func):
    with handle_interrupt(func) as wrapped_func:
        wrapped_func()


@handle_interrupt
def main():
    global num_subs
    subreddit_file = 'subs'
    print(f"Opening subs file: {subreddit_file}")
    with open(subreddit_file) as f:
        subreddit_names = f.read().splitlines()
        total_num_subs = len(subreddit_names)
        sub_counter = 0
        print(f"Loaded {num_subs} subreddits")
        for subreddit_name in subreddit_names:
            print(f"Gathering JSON for {subreddit_name}")
            dump_subreddit_json(subreddit_name)

if __name__ == '__main__':
    main_func(main)
