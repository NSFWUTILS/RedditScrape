import praw
import urllib.request
import os
import csv
import shutil
import subprocess
import sys
import time
import configparser
from utils import checkMime, download_video_from_text_file
from redgifdl import download

# Setup the configparser to read the config file named 'config'
config = configparser.ConfigParser()
config.read("config")
client_id = config["CONFIG"]["REDDIT_CLIENT_ID"]
client_secret = config["CONFIG"]["REDDIT_CLIENT_SECRET"]
client_user_agent = config["CONFIG"]["REDDIT_USER_AGENT"]
post_limit = config["CONFIG"]["REDDIT_POST_LIMIT"]
sort_type = config["CONFIG"]["REDDIT_SORT_METHOD"]
time_period = config["CONFIG"]["REDDIT_TIME_PERIOD"]

# Set up the root filesystem folder
root_folder = config["CONFIG"]["MEDIA_FOLDER"]

# Set up the Reddit API client
reddit = praw.Reddit(client_id=client_id, client_secret=client_secret, user_agent='YataGPT')

print(f"Creating all sub-folders in: {root_folder}")
print(f"Showing the first {post_limit} posts sorted by {sort_type}")

# Set up the CSV file
csv_file = 'results.csv'
csv_fields = ['subreddit', 'title', 'author', 'upvotes', 'filename']

# Set up the set to keep track of downloaded URLs
downloaded_urls = set()

# Read in the list of subreddit names from the text file
subreddit_file = 'subs'
with open(subreddit_file) as f:
    subreddit_names = f.read().splitlines()
badSubs = []
# Loop over each subreddit name
for subreddit_name in subreddit_names:
    # Set up the subfolder for the subreddit
    subreddit_folder = os.path.join(root_folder, subreddit_name)
    os.makedirs(subreddit_folder, exist_ok=True)

    # Query all of the posts in the subreddit
    subreddit = reddit.subreddit(subreddit_name)
    try:
        subreddit.id
        print(f"### Processing Sub {subreddit_name}")
    except:
        print(f"### Sub {subreddit_name} doesn't exist")
        badSubs.append(subreddit_name)
        continue
    #for post in subreddit.top(limit=int(post_limit)):
    #for post in getattr(subreddit, reddit_sort)(limit=int(post_limit)):
    for post in getattr(subreddit, sort_type)(time_filter=time_period, limit=int(post_limit)):
        
        # Check if the post is a link to imgur.com
        #if "redgifs.com" not in post.url and post.url not in downloaded_urls:
        if post.url not in downloaded_urls:
            #print(f"Post Title: {post.title}")
            #print(f"Post URL: {post.url}")
            
            # Download the media
            file_name = os.path.basename(post.url)
            file_path = os.path.join(subreddit_folder, file_name)
            if os.path.exists(file_path):
                # Skip the download if the file already exists
                #print(f"Skipping download for {file_path} (already exists)")
                continue
            try:
                if "redgifs.com" in post.url or "gfycat.com" in post.url:
#                    download.url_file(redgifs_url=post.url, filename=file_path)
                    galleryCommand = 'python -m gallery_dl -D ' + subreddit_folder + ' "' + post.url + '"'
                    #print(f"DEBUG: galleryCommand: {galleryCommand}")
                    os.system(galleryCommand)
                    # print(f"Original post: {post.permalink}")
                    # print(f"Testing: Downloaded {file_path} from redgifs")
                    continue
                urllib.request.urlretrieve(post.url, file_path)
                fileType = checkMime(file_path)
                if "text" in fileType:
                   newURL = download_video_from_text_file(file_path) 
                   #print(f"Turns out {file_path} was text")
                   #print(f" - Downloading {newURL} instead")
                   urllib.request.urlretrieve(newURL, file_path)
                   downloaded_urls.add(newURL)
                downloaded_urls.add(post.url)
            except Exception as e:
                pass
                print(f"Error processiong url:{post.url} - {e}")

            # Store the metadata in the CSV file
            with open(csv_file, mode='a', newline='') as f:
                try: 
                    writer = csv.DictWriter(f, fieldnames=csv_fields)
                    writer.writerow({'subreddit': subreddit_name, 'title': post.title, 'author': post.author.name, 'upvotes': post.score, 'filename': file_name})
                except Exception as e:
                    print(f"Error updating CSV: {e}")
            time.sleep(1)



print(f"List of bad subs: {badSubs}")    

    