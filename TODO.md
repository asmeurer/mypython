# TODOs

- operate-and-get-next (C-o) (https://github.com/jonathanslenders/python-prompt-toolkit/issues/416)
- Fix scrolling with mouse support
- Better packaging
- Pygments thinks matmul @ is a decorator (https://bitbucket.org/birkenfeld/pygments-main/issues/1194/support-python-35s-matrix-multiplication)
- pygments won't color True/False/None separately
- pygments won't color variable names separately
- pygments doesn't color """ yellow until it is completed
- Have to press TAB too many times to complete
- Spellcheck on NameError
- Jedi completion within multiline inputs
- Better indication when no tab completions are found
- History browser (like ptpython)
- Different continuation prompt for soft- and hard-wrapping.
- Variable definitions in %timeit calls don't apply to the rest of the session
- Tests for multiline history search
- Deleting selected text messes up indentation (https://github.com/jonathanslenders/python-prompt-toolkit/issues/324)
- pudb inside mypython doesn't work
- Cursor position with M-;
- Load the cat asynchronously
- If pudb crashes mypython crashes
- Magics at end of multiline?
- Python 3.6
- Mypython doesn't run in the current conda env
- Tests for command queue
- Completion is too damn slow
- Yanked text gets removed from kill ring too easily
- Garbage when pasting multiple lines
- Keep track of execution time of each prompt
- Selection is disabled after one C-c <
- LaTeX math
- Clear mypython variables when leaving PuDB shell
- Add key to hide prompts
- Confusing when line is exactly the terminal width
- Enter in the middle of a line in multiline tries to execute
- Some kind of session object
- Make the doctest mode session local (part of the builtins)
- TAB in the middle of a line should indent
- Make the command queue not use input
- Should not allow newline inside single quote string, even in multiline
- Forward/backward sexp doesn't work unless it's on a parenthesis
- Print %time time after the output
- Add line profiler magic
- Prompt number not incremented when %pudb exits with traceback
- SyntaxError from the tokenizing functions on invalid # -*- coding: invalid -*-
- tokenize based dedent
- Extra indentation when pasting a function from a doctest
- Importing pyplot causes Python app to become focused
- Make In a list like IPython?
- --cmd items being kept in history (see https://github.com/jonathanslenders/python-prompt-toolkit/issues/762)
- Multiline prompt paste fails when there are no continuation prompts
- PuDB needs a new filename even when the old one's prompt didn't return
- Newlines at the end of the prompt not being cleared from history (https://github.com/prompt-toolkit/python-prompt-toolkit/pull/800)
- Issue pasting multiline prompt with spaces after prompts
- Broken pretty printing with solveset(log(x) - y, x)
- Regexes don't work with Unicode characters correctly
  (https://stackoverflow.com/questions/36187349/python-regex-for-unicode-capitalized-words)
- dir completion includes global names on attribute completion
- Wrong line numbers on traceback if the input that defined the function raise
  an exception.
- Add line profiler support
- Fix pudb timeout stringifier

## 2.0 TODOs

- Make all keybindings assign a Document
- Figure out how to set the prompt-toolkit exception handler
- Jedi warnings printed to terminal during completion (`simplify(x).TAB`)
