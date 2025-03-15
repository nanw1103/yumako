#!/usr/bin/env -S python -W ignore

# from yumako import args, env
# import yumako.args as args
# import yumako.env as env

from yumako.state import StateFile

# print(yumako.args.get("foo"))
# print(yumako.env.get("foo"))
# print(args2.get("foo"))
# print(env2.get("foo"))
# print(args3.get("foo"))  # pylint: disable=no-member
# print(env3.get("foo"))  # pylint: disable=no-member

# print(yumako.args)
# print(yumako.env)


state1 = StateFile("temp.json")
state1.set("key", "value")

# Create a new instance to verify it's on disk
state2 = StateFile("temp.json")
v = state2.get("key")
print(v)
