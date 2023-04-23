from __future__ import unicode_literals
import magic
import re
import urllib.request
#from RedDownloader import RedDownloader
from redgifdl import download
#import youtube_dl
from gallery_dl import job, config
import subprocess


def checkMime(fileName):
    # Create a new magic object
    mime = magic.Magic(mime=True)

    # Get the MIME type of a file
    mime_type = mime.from_file(fileName)

    # Print the MIME type
    #print(f"{fileName} is of type {mime_type}")
    return mime_type

def youtube(URL):
    ydl_opts = {}
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        ydl.download([URL])

def clean_title(title):
    # Replace spaces with underscores
    title = title.replace(' ', '_')
    # Remove non-alphanumeric characters (except dashes and underscores)
    title = re.sub(r'[^\w-]', '', title)
    return title

def gallery(URL):
    config.load()
    config.set(("extractor",), "base-directory", f"./tmp")
    job.DownloadJob(URL).run()

# def gallery_download(subreddit_folder, post):
#     reddit_url = "https://www.reddit.com" + post.permalink
#     post_title = clean_title(post.title)
#     #print(f"Reddit URL: {reddit_url}",flush=True)
#     #print(f"Post Permalink: {post.permalink}",flush=True)
#     #gallery_command = f'python -m gallery_dl -D {subreddit_folder} -f "{post_title}.{extension} "{post.url}" '
#     gallery_command = f'python -m gallery_dl -D {subreddit_folder} -f "{post_title}.{{extension}}" {reddit_url} '
#     #print(f"Running gallery: {gallery_command}",flush=True)
#     result = subprocess.run(gallery_command, shell=True, text=True, capture_output=True)
#     #print(f"Result STDOUT: {result.stdout}",flush=True)
#     #print(f"Result STDERR: {result.stderr}",flush=True)
#     if "#" in result.stdout:
#         #print(f"Skipping: {post_title}",flush=True)
#         #skipped_files.put(post_title)
#     return result.stdout


def download_video_from_text_file(file_path):
    # Read the file contents
    with open(file_path, "r") as f:
        file_contents = f.read()
    
    # Search for the og:video:secure_url line using regular expressions
    match = re.search(r'<meta property="og:video:secure_url"  content="(.+?)" />', file_contents)
    
    # If a match is found, get the content URL and download the file
    if match:
        content_url = match.group(1)
        file_name = content_url.split("/")[-1]
        #urllib.request.urlretrieve(content_url, file_name)
        return content_url

if __name__ == "__main__":
    testURL = "https://redgifs.com/watch/acclaimedadorabletigerbeetle"
    #testURL = "https://gfycat.com/equatorialagreeablegalapagosmockingbird"
    #youtube(testURL)
    #download.url_file(redgifs_url=testURL, filename="foo.mp4")
    gallery(testURL)
    pass
