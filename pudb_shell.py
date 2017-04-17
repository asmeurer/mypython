"""
Custom shell for PuDB. Set this as the custom shell in the PuDB settings to
use mypython as the ! shell in PuDB.
"""

import os
import sys
import inspect

# We cannot use __file__ because it isn't defined with execfile
mypython_path = inspect.getframeinfo(inspect.currentframe()).filename
mypython_dir = os.path.dirname(mypython_path)

if os.path.isdir(mypython_dir):
    sys.path.insert(0, mypython_dir)

from mypython import run_shell as pudb_shell
