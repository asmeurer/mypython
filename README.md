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

- Fancy emoji numbered prompts.
- Keyboard shortcuts configured exactly the way I like them.
- Outputs saved as `_NUM`. Previous outputs saved in `_`, `__`, and `___`.
- Support for bracketed paste (pasting stuff in the terminal "just works"
  without the need for any %paste magic or a special "paste" mode).
- prompts are stripped automatically from pasted text.
- Emacs command editing keybindings.
- Automatic syntax highlighting.
- Matching and mismatching parentheses highlighting.
- Tracebacks for stuff defined interactively show the code line.
- Tab completion using [Jedi](https://github.com/davidhalter/jedi).
- Per-terminal history.
- A nice theme (the same one I use in emacs, called "1am", based on XCode's
  "midnight").
- `stuff?` shows the help for `stuff`. Works even if `stuff` is a complex
  expression. Does the right thing for NumPy ufuncs.
- `stuff??` shows the source for `stuff`. Works even if `stuff` was defined
  interactively.
- `%time` and `%timeit` magic commands. `%timeit` displays a histogram of
  times in the terminal (using iTerm2).
- `%doctest` mode to emulate standard Python REPL (for copy-paste purposes).
- `%sympy` magic (works like `sympy.init_session()`.
- `%pudb` magic to run code in [PuDB](https://documen.tician.de/pudb/).
  Debugging functions defined interactively is possible.
- SymPy objects automatically pretty print.
- Automatic "error" mode on syntax error, that moves the cursor to the error.
- [Shell integration](https://www.iterm2.com/documentation-shell-integration.html) with iTerm2.
- GUI Matplotlib plots on macOS work correctly.
- At startup you get a [cat](https://github.com/asmeurer/catimg).

And some [other stuff](TODO.md) that I haven't implemented yet.

Most of this stuff either comes for free from prompt-toolkit or was really easy
to implement, in some cases by modifying some code from other libraries
(ptpython, ipython, sympy, the Python standard library).

# Installation

I haven't packaged it yet. For now you can clone the repo and run
`./bin/mypython`.

It requires the following packages, which can be installed
from [conda-forge](https://conda-forge.github.io/):

- prompt_toolkit
- pygments
- iterm2_tools
- catimg
- ipython
- matplotlib
- seaborn

# Configuration

There is none. It's already configured the way I like it.

# Features and bugs and stuff

I wrote this for me. You can request features, submit PRs, and report bugs,
but be aware that I won't accept any PR unless it's a feature I want. I'm
really not designing this to be used by other people.

# Acknowledgments

Thanks to Jonathan Slenders for prompt-toolkit and ptpython (which I borrowed
some of the more tricky things like Python multiline and Jedi completion
from). Basically all the fancy stuff here is coming from prompt-toolkit. I
just combined it together into a REPL that I like. Thanks to the IPython guys
for figuring out the matplotlib eventloop stuff (which I could never do on my
own), and for inspiring many of the features I've implemented.

# License

[MIT](LICENSE.md).

Licenses for code taken and modified from ptpython, IPython, prompt-toolkit,
SymPy, and the Python standard library are at the top of the respective files.
