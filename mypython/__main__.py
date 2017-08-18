# PYTHON_ARGCOMPLETE_OK
"""
mypython

A Python REPL the way I like it.
"""

import argparse

from .mypython import run_shell
from . import mypython

def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--cmd", "-c", metavar="CMD", action="store",
        help="""Execute the given command at startup.""")
    parser.add_argument("--quiet", "-q", "-Q", action="store_true", help="""Don't
        print the startup messages.""")
    parser.add_argument("--doctest-mode", "-d", action="store_true",
        help="""Enable doctest mode. Mimics the default Python prompt.""")
    parser.add_argument("--cat", action="store_true",
        help="""Print an image of a cat at startup. Requires catimg to be installed.""")
    parser.add_argument("--debug", "-D", action="store_true",
        help="""Enable debug mode. The same as -c '%%debug'.""")

    try:
        import argcomplete
        argcomplete.autocomplete(parser)
    except ImportError:
        pass
    args = parser.parse_args()

    if args.debug:
        mypython.DEBUG = True
        print("mypython debugging mode enabled")

    if args.doctest_mode:
        mypython.DOCTEST_MODE = True

    return run_shell(quiet=args.quiet, cmd=args.cmd, cat=args.cat)

if __name__ == '__main__':
    main()
