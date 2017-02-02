# mypython

A Python REPL the way I like it.

## What? Why?

I was unsatisfied
with
[all](https://ipython.readthedocs.io/en/stable/whatsnew/version4.html) [the](https://ipython.readthedocs.io/en/stable/whatsnew/version5.html) [existing](https://github.com/jonathanslenders/ptpython) [Python](http://xon.sh/) [interpreter](https://bpython-interpreter.org/) [options](https://docs.python.org/3.6/tutorial/interpreter.html).
None quite worked the way I liked them to, even after attempting to configure
them (often a frustrating experience).

So instead I wrote my own. Turns out it's really easy.

[prompt-toolkit](https://python-prompt-toolkit.readthedocs.io/en/latest/) is a
nice framework for creating custom REPLs. It took under an hour to create a
basic Python REPL, and only a few days to add most of the features I like to
it. REPLs created with prompt-toolkit are really nice. They support advanced
features like syntax highlighting, multiline editing, and popup tab completion
without any additional work (unlike REPLs based on readline).

# Features

- IPython-style numbered In/Out prompts.
- Multiline editing with sane keyboard shortcuts (M-Enter always adds a
  newline, Enter adds a newline at a continuation, or executes if you enter
  two blank lines at the end).
- Up arrow (at the top of the line) always goes to the previous command,
  regardless of the text before the cursor.
- Same with down arrow.
- You don't have to up/down arrow a bunch to navigate history with multiline
  statements.
- C-n/C-p always navigate history.
- C-</C-> do what you'd expect from emacs.
- C-{/C-} do what you'd expect from emacs.
- Outputs saved as `_NUM`. Previous outputs saved in `_`, `__`, and `___`.
- M-p and M-P do reverse and forward history search (show previous commands
  that start with the text before the cursor).
- Support for bracketed paste (pasting stuff in the terminal "just works"
  without the need for any %paste magic or a special "paste" mode).
- Emacs command editing keybindings.
- Automatic syntax highlighting.
- Matching parentheses highlighting.
- Tab completion using [Jedi](https://github.com/davidhalter/jedi).
- Per-terminal history.
- A nice theme (the same one I use in emacs, called "1am", based on XCode's
  "midnight").
- `stuff?` shows the help for `stuff`. Works even if `stuff` is a complex
  expression.
- `stuff??` shows the source for `stuff`. Works even if `stuff` was defined
  interactively.
- Control-D always exits, regardless of where the cursor is.
- Automatic "error" mode on syntax error. Move the cursor to the error.
- [Shell integration](https://www.iterm2.com/documentation-shell-integration.html) with iTerm2.
- At startup you get a [cat](https://github.com/asmeurer/catimg).

And some [other stuff](TODO.md) that I haven't implemented yet.

# Installation

I haven't packaged it yet. For now you can clone the repo and run
`./bin/mypython`.

It requires the following packages, which can be installed
from [conda-forge](https://conda-forge.github.io/):

- prompt_toolkit
- pygments
- iterm2_tools
- catimg

# Configuration

There is none. It's already configured the way I like it.

# Features and bugs and stuff

I wrote this for me. You can request features, submit PRs, and report bugs,
but I'm be aware that I won't accept any PR unless it's a feature I want. I'm
really not designing this to be used by other people.

# Acknowledgments

Thanks to Jonathan Slenders for prompt-toolkit and ptpython (which I borrowed
some of the more tricky things like Python multiline and Jedi completion
from). Basically all the fancy stuff here is coming from prompt-toolkit. I
just combined it together into a REPL that I like.
