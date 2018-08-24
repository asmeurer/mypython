"""
Custom shell for PuDB. Set this as the custom shell in the PuDB settings to
use mypython as the ! shell in PuDB.
"""

import os
import sys
import inspect

from pudb.shell import SetPropagatingDict

# We cannot use __file__ because it isn't defined with execfile
mypython_path = inspect.getframeinfo(inspect.currentframe()).filename
mypython_dir = os.path.dirname(mypython_path)

if os.path.isdir(mypython_dir):
    sys.path.insert(0, mypython_dir)

from mypython import run_shell

prompts = ("\N{BUG}"*2, "\N{LADY BEETLE}"*2)

def pudb_shell(_globals, _locals):
    try:
        tty_name = os.path.basename(os.ttyname(sys.stdout.fileno()))
    except OSError:
        tty_name = 'unknown'

    # This makes it so that assignments in the shell act like globals
    # assignments
    ns = SetPropagatingDict([_locals, _globals], _locals)

    return run_shell(ns, ns, quiet=True,
        history_file='~/.mypython/history/pudb_%s_history' % tty_name,
        in_out=prompts)
