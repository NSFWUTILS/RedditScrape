# RedditScrapeNSFW
With the news that reddit will soon be charging for API access, and that imgur is no longer hosting NSFW media, I wanted to create something to help download things while the getting is good.  I've tested this on Mac and Ubuntu with python 3.9.7

The code is designed to run in a concurrent fashion (sort of like multi-threading) to help with performance. 

And a big thanks to the creator(s) of [gallery-dl](https://github.com/mikf/gallery-dl) as it makes it easy to support imgur.com, redgif.com, and gfycat.com.

# Getting Started
The following sections should help get you started. 

## Setup Reddit API
Visit [this link](https://www.reddit.com/prefs/apps) to create an app

At the bottom you should see a button to create an app, click on it and fill in the details so it looks something like this: 

![Create Reddit App](/images/create_reddit_app.png)

Once you click on the `create app` button again, you should see it displayed above. Click on the `edit` link in the bottom left corner to get the details you need. You should see something like this:
![Reddit App Details](/images/reddit_app_details.png)

The box in green represents your "Client ID"
The box in red represents your "Client Secret"

**DO NOT SHARE THESE WITH ANYONE ELSE**

## Setup the Script
- Clone the repo
- cd into the repo folder
- rename `subs.sample` to `subs` and modify accordingly. Make sure you enter each sub-reddit you want to download on its own line, and this **IS** CaSE SEnsITive
- rename `config.sample` to `config`
- Edit the file `config` with your values
- Install the required python modules: `python -m pip install -r requirements.txt`

## Configure the Script
I use the file `config` to control all of the important variables. Below are some of the things you need to understand and adjust to your own liking. 

### Performance Considerations
I've got this setup to run on a fairly beefy VM (24 cores and 20 gigs of ram). Consider modifying the two values in `config`:
- `MAX_WORKERS`
- `POOL_SIZE`

These values should be more in line with how many CPU cores you have (as a very rough estimate). You can try tweaking these, but putting them too high can kill your system or introduce lots of errors. There is a trade off here, so higher numbers isn't always better. 

### Sorting Posts
I am using the praw module to generate the list of files to download. There are 3 settings in your `config` file that matter here:
- `REDDIT_SORT_METHOD`
- `REDDIT_TIME_PERIOD`
- `REDDIT_POST_LIMIT`

The default settings give you the first `100` `top` posts from `all` time 

Here is a list of possible sorting options for subreddit posts in PRAW:

- hot: The most popular posts, taking both upvotes and downvotes into account.
- new:The most recently submitted posts.
- rising: Posts that are quickly gaining upvotes and comments.
- controversial: Posts with a high number of both upvotes and downvotes.
- top: The highest-scoring (upvotes minus downvotes) posts of all time, or within a specified time range.

**For top and controversial**, you can also specify a time filter with the following options:

- all - All time.
- year - Within the past year.
- month - Within the past month.
- week - Within the past week.
- day - Within the past day.
- hour - Within the past hour.

## Running the script
Make sure you are in the same folder as the script and try running `python crawler.py`. 

Eventually a progress indicator will show up and you'll notice it's not very accurate. Due to the multi-threaded nature of this I couldn't figure out a way to get a reliable count. Basically it starts downloading files while it's still discovering just how many files it has to download. Eventually it should settle down some and give a more accurate reading. 

If things work, the script will create a sub-folder for each sub-reddit inside of whatever folder you specified as `MEDIA_FOLDER` in your `config` file. 

If any of the entries in your list of subs don't exist (You spelled them wrong etc) it will let you know at the end: `List of bad subs: ['SomeSubThatDoesn'tExist']`

Results can be seen in `output_log.txt` once it finishes. 

## Running in the background
If you want to make sure this keeps running in case you get disconnected or something, you can run it in the background with something like `nohup python crawler.py > nohup.log &`. You can monitor the status of this using `jobs` and use `kill %1` if you need to cancel it. 

## Stopping the script
**IMPORTANT:** This script runs in a threaded manner so you can't just `ctrl+c` your way out. If you want to cancel this you'll have to use `ctrl+z` first, then once it has stopped you can run `kill %1`. 

# Downloading your own saved items
I've created `saved.py` for people who want to run this against their own saved items. It will require you add your reddit username and password to the config file. Once you do that, just run `python saved.py` and it should work in a similar fashion, just slower (no threading here). It looks for anything in your saved items that points to imgur, redgif, or gyfcat and puts them in the same folder structure as the other stuff. 

There's also a config setting (`REDDIT_SAVED_LIMIT`) for how many of your saved items it should retrieve, defaults to 500. 

# To Do
A few things I'd like to do if time permits....
- Use something like sqllite to store all of this, that opens up some possibilities down the road for easier storing/tagging/classification. 
- Implement proper logging
- Look into making this asynchronous to increase performance: (This is done) 