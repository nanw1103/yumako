#!/usr/bin/env -S python -W ignore

from yumako.state import default_state

# init_default(".state")

state = default_state()

# Update a state. This is by default persisted to disk.
state.set("k1", "v1")

# Read a state.This is by default read from RAM cache.
# But if this is a new process, it will also be read from disk.
v = state.get("k1")
print(v)

# Cleanup the state file.
state.delete()
