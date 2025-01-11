#!/usr/bin/env -S python3 -W ignore

from datetime import timedelta

from yumako import time

# Smart conversion from human-friendly format to python vanilla datetime
dt = time.of("-1d")

print(dt)  # python vanilla datetime

# Convert human delta to seconds
seconds = time.duration("3m4s")

delta = timedelta(seconds=seconds)

# Display timedelta to human readable format
print(time.display(delta))  # 3m4s
