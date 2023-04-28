# RedditScrape
With the news that reddit will soon be charging for API access, and that imgur is no longer hosting NSFW media, I wanted to create something to help download things while the getting is good.  I've tested this on Mac and Ubuntu with python 3.9.7

The code is designed to run in a concurrent fashion (sort of like multi-threading) to help with performance. 

And a big thanks to the creator(s) of [gallery-dl](https://github.com/mikf/gallery-dl) as it makes it easy to support imgur.com, redgif.com, and gfycat.com.

# Major Changes
Thanks to the contributions of a fellow anonymous redditor we now pull data from push shift. This has a lot of advantages, mainly no need for reddit credentials, but also being able to suck down as much as you want for a given subreddit. Seriously, I have over 3.3 MILLION entries in my JSON for *gonewild* and it's still going. 

# Getting Started
The following sections should help get you started. 

## Setup the Script
- Clone the repo
- cd into the repo folder
- rename `subs.sample` to `subs` and modify accordingly. Make sure you enter each sub-reddit you want to download on its own line, and this **IS** CaSE SEnsITive
- rename `config.sample` to `config`
- Make sure you update the location of `MEDIA_FOLDER` in your config file. 
- Install the required python modules: `python -m pip install -r requirements.txt`

## Running the script
Running this script is now a two step process. 

### Download data from push shift
To begin this process, run `python threaded-acquire.py`. If you have your `subs` file setup properly, it will begin to query push shift for all of the posts ever made to that sub. These will be stored in `MEDIA_FOLDER`/json

**Warning:** Some of the more popular subs, like *gonewild* are **absolutely huge**. I've been working on downloading it for 2 days now. The JSON text alone is currently 9 gigs and climbing. I recommend you skip this one for now and come back to it later. 

This script is designed to run with 4 threads, so it should start trying to download data from 4 subs at once.  When it's done, you can move on to the next script. 

### Downloading the Media
Now that you've downloaded the JSON data from push shift, you can start the actual download process by running `python json-crawler.py`. This will iterate through all of your JSON files to build one massive list of things to download. It will then thread this process (Should be based on what you have for `MAX_WORKERS` in your config file) to start downloading as fast as it can. 

## Running in the background
If you want to make sure this keeps running in case you get disconnected or something, you can run it in the background with something like `nohup python json-crawler.py > nohup.log &`. You can monitor the status of this using `jobs` and use `kill %1` if you need to cancel it. 

## Stopping the script
**IMPORTANT:** This script runs in a threaded manner so you can't just `ctrl+c` your way out. If you want to cancel this you'll have to use `ctrl+z` first, then once it has stopped you can run `kill %1`. 

# Examining and Troubleshooting
The script will download files into 3 folders underneath `MEDIA_FOLDER`:
- `/json`: The raw json from push shift
- `/json-output`: my very streamlined json output in case you want to use the data to categorize/rename etc. Contains post_id, author, permalink, url etc. 
- `/subreddits`: The root folder where all subreddits will be placed

## Troubleshooting
There's not a whole lot of logging for `threaded-acquire.py` - the original author did a tremendous job making it robust (seriously, very well done). 

For the `json-crawler.py` I output everything into `output_log.txt`. If things aren't working that is the first place you should look. 

### Steps to take
If things aren't working, please verify the following:
- Python Version: This was written and tested using python 3.9.7 on linux. Verify the version of python you're using via `python --version`. I suspect anything that is 3.9 or later should work. 
- Config File: Make sure you've followed the instructions and specified the appropriate value for `MEDIA_FOLDER` in your config file (not config.sample)
- Subreddit File: This script is set to look for a list of subs in the file `subs`. There should be one sub per line, and they are CasE SEnsitIVe. 
- Python Modules: Make sure you have installed all of the python modules. You can run `python -m pip install -r requirements.txt`


# Downloading json data (Original instructions from anonymous contributor)
Information about submissions (including links, upvotes, author, etc.) can be saved for further local processing. To save local subreddit data from the pushshift archives, run a command like this:

    `python ./acquire_sub_posts_json.py --subreddit eyebleach`

This will acquire submission data about every archived post in the "eyebleach" subreddit. This script will hang for a while every now and again, as the pushshift server is unreliable. Recommend doing an initial test on a smaller subreddit, like "girlskissing".

Scripts for doing further processing on this data, and downloading images, should be added later...

# To Do
A few things I'd like to do if time permits....
- Use something like sqllite to store all of this, that opens up some possibilities down the road for easier storing/tagging/classification. 
- Implement proper logging
- Look into making this asynchronous to increase performance: (This is done) 