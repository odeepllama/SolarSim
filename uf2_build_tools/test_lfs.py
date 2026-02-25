import littlefs
# Create a LittleFS filesystem
fs = littlefs.LittleFS(
    block_size=4096,
    block_count=2,
    name_max=32,
    read_size=32,
    prog_size=32,
    lookahead_size=32
)
with fs.open('/test.txt', 'w') as f:
    f.write("Hello")
print(type(fs.context.buffer))
print(len(fs.context.buffer))
