"""
mypython

A Python REPL the way I like it.
"""

import argparse

from .mypython import default_history_filename, run_shell
from . import mypython

def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--cmd", "-c", metavar="CMD", default=[],
        action="append", help="""Execute the given command at startup.""")
    parser.add_argument("--isympy", action="store_true",
        help="""Start isympy. Equivalent to -c '%%sympy'.""")
    parser.add_argument("--quiet", "-q", "-Q", action="store_true", help="""Don't
        print the startup messages.""")
    parser.add_argument("--doctest-mode", "-d", action="store_true",
        help="""Enable doctest mode. Mimics the default Python prompt.""")
    parser.add_argument("--history-file", metavar="HISTORY_FILE", default=None,
        action="store", help=f"""Use the given file for the command history.
        For this terminal, this defaults to {default_history_filename()}""")
    parser.add_argument("--debug", "-D", action="store_true",
        help="""Enable debug mode. Equivalent to -c '%%debug'.""")
    parser.add_argument('--exit', action='store_true', help="""Exit immediately, after
        running any --cmd commands.""")

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
        mypython.doctest_mode()

    if args.isympy:
        args.cmd.append('%sympy')

    return run_shell(quiet=args.quiet, cmd=args.cmd, _exit=args.exit,
                     history_file=args.history_file)

if __name__ == '__main__':
    main()
