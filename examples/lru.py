#!/usr/bin/env -S python3 -W ignore

from yumako.lru import LRUDict, LRUSet

# Yumako utilities are highly performant:

lru = LRUDict()
lru[1] = True
lru["hello"] = "mortal"
lru["ユマ果"] = "💖"
print(lru)

lru_set = LRUSet()
lru_set.add("ユマ果")
print(lru_set)
