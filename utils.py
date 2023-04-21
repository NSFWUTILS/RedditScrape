from __future__ import unicode_literals
import magic
import re
import urllib.request
#from RedDownloader import RedDownloader
from redgifdl import download
#import youtube_dl
from gallery_dl import job, config


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

def gallery(URL):
    config.load()
    config.set(("extractor",), "base-directory", f"./tmp")
    job.DownloadJob(URL).run()

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
