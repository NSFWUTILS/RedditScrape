import os
import configparser
import praw
import subprocess
from utils import checkMime, download_video_from_text_file

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
reddit_user_name = config["CONFIG"]["REDDIT_USER_NAME"]
reddit_user_pass = config["CONFIG"]["REDDIT_USER_PASS"]
reddit_saved_limit = config["CONFIG"]["REDDIT_SAVED_LIMIT"]
root_folder = config["CONFIG"]["MEDIA_FOLDER"]

reddit = praw.Reddit(
    client_id=client_id, 
    client_secret=client_secret, 
    user_agent=client_user_agent,
    username = reddit_user_name,
    password = reddit_user_pass
    )



#saved_items = reddit.user.me().saved(limit=50)
saved_items = reddit.user.me().saved(limit=int(reddit_saved_limit))


for item in saved_items:
    if isinstance(item, praw.models.Submission):
        # item is a post
        if "imgur" in item.url or "redgif" in item.url or "gfycat" in item.url:
            subreddit_name = item.subreddit
            subreddit_folder = os.path.join(root_folder, str(subreddit_name))
            os.makedirs(subreddit_folder, exist_ok=True)
            file_name = os.path.basename(item.url)
            file_path = os.path.join(str(subreddit_folder), file_name)
            gallery_command = f'python -m gallery_dl -D {subreddit_folder} "{item.url}" '
            result = subprocess.run(gallery_command, shell=True, text=True, capture_output=True)
            print(f"Downloaded {result.stdout} ")


