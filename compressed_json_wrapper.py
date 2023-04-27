import gzip
import json
from itertools import islice

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
    file_path = 'your_compressed_json_file.json.gz'
    for entry in read_gzipped_json(file_path):
        print(entry)
    
    
    # Write file
    entries = [{'key1': 'value1'}, {'key2': 'value2'}, {'key3': 'value3'}]
    output_file_path = 'output_compressed_json_file.json.gz'
    
    writer = GzippedJsonWriter(output_file_path)
    
    for entry in entries:
        writer.add_entry(entry)
    
    writer.finish()
