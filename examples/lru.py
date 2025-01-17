#!/usr/bin/env -S python3 -W ignore

from yumako.lru import LRUDict

lru = LRUDict(1000)
lru[1] = 2
lru["hello"] = "ユマ果"

print(lru)
