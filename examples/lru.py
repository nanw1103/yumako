#!/usr/bin/env -S python3 -W ignore

import yumako

# Yumako utilities are designed for human:
print(yumako.time.of("2025-01-17"))
print(yumako.time.of("-3d"))


#Yumako utilities are highly performant:
lru = yumako.lru.LRUDict()
lru[1] = True
lru["hello"] = "mortal"
print(lru)

lru_set = yumako.lru.LRUSet()
lru_set.add("ユマ果")
print(lru_set)