#!/usr/bin/env -S python3 -W ignore

from datetime import timedelta

import yumako
# Yumako submodules are loaded only when needed.

# ---------------------------------------
# Yumako utilities are designed for human
# ---------------------------------------
print(yumako.time.of("2023-12-04T12:30:45.000+00:00"))  # Most readable format
print(yumako.time.of("-3d"))  # 3 days ago

seconds = yumako.time.duration("3m4s")  # 3m4s -> 184 seconds
delta = timedelta(seconds=seconds)
print(yumako.time.display(delta))  # 3m4s

# ---------------------------------------
# Yumako utilities are highly performant
# ---------------------------------------
lru = yumako.lru.LRUDict()
lru[1] = True
lru["hello"] = "mortal"
print(lru)

lru_set = yumako.lru.LRUSet()
lru_set.add("ユマ果")
print(lru_set)
