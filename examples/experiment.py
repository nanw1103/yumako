#!/usr/bin/env -S python -W ignore

# from yumako import args, env
# import yumako.args as args
# import yumako.env as env

import yumako
import yumako.args as args3
import yumako.env as env3
from yumako import args as args2
from yumako import env as env2

print(yumako.args.get("foo"))
print(yumako.env.get("foo"))
print(args2.get("foo"))
print(env2.get("foo"))
print(args3.get("foo"))  # pylint: disable=no-member
print(env3.get("foo"))  # pylint: disable=no-member
