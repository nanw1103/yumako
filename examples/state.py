#!/usr/bin/env -S python -W ignore

from yumako.state import state_file

state = state_file(".state")  # Create a state file.

state.k1 = "v1"  # Update a state. This is by default persisted to disk.
print(state.k1)  # "v1". Load from disk if not in RAM cache.
print(state.k2)  # None.

# Cleanup the state file.
state.delete()
