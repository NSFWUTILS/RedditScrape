import gzip
import json
from itertools import islice
from urllib.parse import urlparse, parse_qs
import re

class GzippedJsonWriter:
    def __init__(self, output_file_path):
        self.file = gzip.open(output_file_path, 'wb')
        self.file.write(b'[')
        self.first_entry = True
    
    def add_entry(self, entry):
        if not self.first_entry:
            self.file.write(b',\n')
        else:
            self.first_entry = False
        
        json_string = json.dumps(entry)
        json_bytes = json_string.encode('utf-8')
        self.file.write(json_bytes)
    
    def finish(self):
        self.file.write(b'\n]')
        self.file.close()

def generate_output(input_file,output_file):
    entries = []
    for entry in read_gzipped_json(file_path):
        #print(entry)
        if "google.com" in str(entry['url']):
            google_url = str(entry['url'])
            parsed_url = re.search(r'url=([^&]+)', google_url).group(1)
            #print(f"Parsed URL: {parsed_url}")
            entry['url'] = parsed_url
            #entry['Google AMP URL']: "True"
        entry_json_to_write = {
            "author" : entry['author'],
            "domain ": entry['domain'],
            "post_id" : entry['id'],
            "permalink" : entry['permalink'],
            "subreddit_name" : entry['subreddit'],
            "url": entry['url'],
            "upvote_ration" : entry['upvote_ratio']
        }
        entries.append(entry_json_to_write)        

    # Write file
    output_file = 'output_compressed_json_file.json.gz'
    
    writer = GzippedJsonWriter(output_file_path)
    
    for entry in entries:
        writer.add_entry(entry)
    
    writer.finish()

def read_gzipped_json(file_path, chunk_size=100):
    """
    Read a gzipped JSON file in chunks and yield each entry as a dictionary.
    
    Args:
        file_path (str): Path to the gzipped JSON file.
        chunk_size (int, optional): The number of lines to read at a time (default is 1000).
    
    Yields:
        dict: A dictionary representing a single entry in the JSON file.
    """
    with gzip.open(file_path, 'rt', encoding='utf-8') as f:
        while True:
            chunk = list(islice(f, chunk_size))
            if not chunk:
                break
            
            for line in chunk:
                # Remove trailing comma and newline, and opening bracket, then parse the line as JSON
                json_line = line.lstrip('[')
                json_line = json_line.rstrip(',\n')
                if json_line != ']':
                    entry = json.loads(json_line)
                    yield entry
                else:
                    # Stop when the closing bracket of the JSON array is encountered
                    break

# Example usage:
if __name__ == '__main__':
    
    # Read file
    file_path = '/tmp/reddit/json/whileshewatches_subreddit_posts_raw.json.gz'
    entries = []
    for entry in read_gzipped_json(file_path):
        #print(entry)
        if "google.com" in str(entry['url']):
            google_url = str(entry['url'])
            parsed_url = re.search(r'url=([^&]+)', google_url).group(1)
            #print(f"Parsed URL: {parsed_url}")
            entry['url'] = parsed_url
            #entry['Google AMP URL']: "True"
        entry_json_to_write = {
            "author" : entry['author'],
            "domain ": entry['domain'],
            "post_id" : entry['id'],
            "permalink" : entry['permalink'],
            "subreddit_name" : entry['subreddit'],
            "url": entry['url'],
            "upvote_ration" : entry['upvote_ratio']
        }
        entries.append(entry_json_to_write)        



    
    
    # Write file
    #entries = [{'key1': 'value1'}, {'key2': 'value2'}, {'key3': 'value3'}]
    output_file_path = 'output_compressed_json_file.json.gz'
    
    writer = GzippedJsonWriter(output_file_path)
    
    for entry in entries:
        writer.add_entry(entry)
    
    writer.finish()
