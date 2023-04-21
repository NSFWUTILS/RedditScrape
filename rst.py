import zstandard as zstd
import time
import json

file_name = "/Volumes/reddit/RS_2023-03.zst"
with open(file_name, 'rb') as fh:
    dctx = zstd.ZstdDecompressor(max_window_size=2147483648)
    with dctx.stream_reader(fh) as reader:
        previous_line = ""
        while True:
            chunk = reader.read(2**24)  # 16mb chunks
            if not chunk:
                break

            string_data = chunk.decode('utf-8')
            lines = string_data.split("\n")
            for i, line in enumerate(lines[:-1]):
                if i == 0:
                    line = previous_line + line
                object = json.loads(line)
                print(line)
                # do something with the object here
            previous_line = lines[-1]