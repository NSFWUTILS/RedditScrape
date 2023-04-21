# RedditScrapeNSFW
With the news that reddit will soon be charging for API access, and that imgur is no longer hosting NSFW media, I wanted to create something to help download things while the getting is good. 

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

## Install libmagic
This is used by the code to analyze if files are text or not (some sites return text files). If they are text, it grabs the proper URL from within the text and downloads that instead. 

On a mac, you just need to do `brew install libmagic` (assuming you already have homebrew installed). 

## Setup the Script
- Clone the repo
- cd into the repo folder
- rename `subs.sample` to `subs` and modify accordingly. Make sure you enter each sub-reddit you want to download on its own line, and this **IS** CaSE SEnsITive
- rename `config.sample` to `config`
- Edit the file `config` with your values
- Install the required python modules: `python -m pip install -r requirements.txt`

That should do it. Make sure you are in the same folder as the script and try running `python crawler.py`

If things work, the script will create a sub-folder for each sub-reddit inside of whatever folder you specified as `MEDIA_FOLDER` in your `config` file. 

If any of the entries in your list of subs don't exist (You spelled them wrong etc) it will let you know at the end: `List of bad subs: ['SomeSubThatDoesn'tExist']`

# To Do
A few things I'd like to do if time permits....
- Use something like sqllite to store all of this, that opens up some possibilities down the road for easier storing/tagging/classification. 
- Implement proper logging
- Look into making this asynchronous to increase performance: (This is done) 