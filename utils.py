from __future__ import unicode_literals
import re
from gallery_dl import job, config
import os
import magic
import youtube_dl

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
    config.set(("extractor",), "base-directory", "./tmp")
    job.DownloadJob(URL).run()


def download_video_from_text_file(file_path):
    # Read the file contents
    #pdb.set_trace()
    target_dir=os.path.split(file_path)[0]
    
    with open(file_path, "r") as f:
        file_contents = f.read()
    
    # Search for the og:video:secure_url line using regular expressions
    match = re.search(r'<meta property="og:video:secure_url"  content="(.+?)" />', file_contents)
    if not match:
        return None
    
    # If a match is found, get the content URL and download the file
    content_url = match.group(1)
    file_name = content_url.split("/")[-1]
    lname=os.path.join(target_dir,file_name)

    if os.path.isfile(lname):
        print(f"The file already exists: {lname}")
        return None

    return content_url
    

if __name__ == "__main__":
    testURL = "https://redgifs.com/watch/acclaimedadorabletigerbeetle"
    #testURL = "https://gfycat.com/equatorialagreeablegalapagosmockingbird"
    #youtube(testURL)
    #download.url_file(redgifs_url=testURL, filename="foo.mp4")
    gallery(testURL)
    pass
