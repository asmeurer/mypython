As [requested](https://twitter.com/jonathan_s/status/898280887908843521) on
Twitter, here is a list of the ways that I've "extended" prompt-toolkit.

To be clear, I actually think all of this is fine, for the most part. I like
how prompt-toolkit's code is very easy to read, once you understand how things
work, and it's quite easy to find the bit that does whatever you don't like
and copy and modify it into your own code to make it do what you want. There
are lots of defaults I don't like. Should prompt-toolkit be changed so that
they can all be configurable to the way I like them via flags? Some of them
for sure, but not all of them.

In quite a few places, once I've modified the code, there's little resilience
to the original, so you can hardly expect the original to be extensible to the
final, but it helped a lot to see how it currently works. Incidentally, this
strategy of "copy and modify" is a huge reason that I love open source and
especially BSD-style open source (you wouldn't be able to do this with GPL or
even LGPL'd code without being forced into that license). But that's a huge
aside.

With only a very few exceptions are there places that prompt-toolkit isn't
extensible in the way I like. I probably could make these work if I hammered
at them hard enough (i.e., copied sufficient code and modified it).

There are a couple of gripes here, but I'm mostly very happy with
prompt-toolkit. My biggest gripes with prompt-toolkit are with its defaults,
but I've found it possible to modify them all, which even if I did so via
copy-pasting, is a testament to prompt-toolkit's modular design. I also just
want to say that I should probably upstream a lot of stuff (a lot of what I
did probably only makes sense to me, but a lot also could be general enough to
be useful as a prompt-toolkit default, e.g.,
https://github.com/jonathanslenders/python-prompt-toolkit/issues/485).

## Difficult to extend

These could be easier to extend. I required some copy-pasting for these.

- Buffer subclass. I use a subclass of Buffer where I override
  history_backward and history_forward. My initial intention was to modify the
  default history search behavior. By default, you either have
  `enable_history_search=True`, in which case up-arrow not at the beginning of
  a prompt does a history search, or it is False, in which case you cannot
  have history search. My preferred behavior is to have the arrow keys always
  navigate history without doing a search (the default readline behavior), but
  I also like to have some keys bound to do history search (I use M-p and
  M-P).  Unfortunately, they are tied together in history_backward and
  history_forward so that you cannot have it both ways. This is actually the
  initial reason that I decided to ditch IPython. In IPython, the flag is set
  to True, and between IPython's architecture and the fact that you have to
  subclass Buffer to change this, it was impossible to do anything about it (I
  couldn't even figure out how to set it to not True in IPython, but that's an
  IPython issue, not a prompt-toolkit issue).

  So I created a subclass with a flag to the history_forward/backward
  functions, which I use in my custom key binding functions for the arrows and
  M-p/M-P.

  Eventually I also implemented some custom history search functionality,
  wherein a history search in a multiline prompt does not consider or affect
  lines above the current one (effectively, I can "merge" prompts from history
  using history search), so I think I would need to have done this eventually
  anyway.

- I have subclassed the `HighlightMatchingBracketProcessor`. I modified the
  function `_get_positions_to_highlight` so that it only
  returns the position before the cursor (my goal is to roughly match emacs's
  show-paren-mode). The default behavior of highlighting both before and under
  the cursor brackets is very confusing.

  Initially this was achieved by copy-pasting it and deleting the if blocks
  that highlighted characters under the cursor. I have since written a much
  better bracket matcher than prompt_toolkit's which is based on Python
  tokenization (it isn't confused by braces in strings), and I use that.

  I also have a custom `apply_transformation` (I have modified it to highlight
  mismatching parens), which is roughly based on the one from prompt-toolkit.
  This is less "extension" and more "prompt-toolkit's" code showed me how to
  write this function.

- Keys: the majority of the stuff here comes from changing key bindings. In a
  lot of cases, this means copying the prompt-toolkit default and adding or
  deleting a single line of code. My main gripe with prompt-toolkit is that
  the default key bindings are all called `_`, so I cannot reuse the
  functions. Except for the named commands, I cannot reuse the prompt-toolkit
  keybinding functions except by copying and pasting the code, even if I just
  want to change the key from the default. For instance, say I just want to
  swap Enter and M-Enter (I actually do more than this myself, but you get the
  idea).

  Several of my bindings change from what prompt-toolkit does entirely (like
  M-</M-> operate on a single prompt instead of the history), and some are
  completely new things. Here are the ones that I think I've modified from
  prompt-toolkit:

  In a lot of cases, I started with prompt-toolkit as a guide, but ended up
  with something so different that I don't know if you can call it
  "copy-paste extension" any more.

    - forward/backward word/killword (M-f/M-b/M-d/M-backspace). Prompt-toolkit's word detection is not
      good (it doesn't even [match readline](https://github.com/jonathanslenders/python-prompt-toolkit/issues/458), although I prefer something even
      more refined so I can easily move across CamelCase).

    - I changed left and right so they wrap in multiline. This isn't really
      related to extensibility but I wanted to mention it here because it's
      one of the most annoying things about the prompt-toolkit defaults.

    - I changed the arrow keys to not do history search, and also to clear the
      selection. I also implemented shift-selection and the arrows without
      shift clear it. I also removed completion navigation (c.f.
      https://github.com/jonathanslenders/python-prompt-toolkit/issues/510).

    - I have a custom BracketedPaste handler that automatically strips prompts
      (so I can copy and paste text from my prompt or a Python/IPython prompt
      and paste it without modification). If it weren't for the default
      handler, I wouldn't have known about the "\r" stripping, which I have
      kept.

    - I removed the execute from the open in editor key binding.

  All in all, a lot of it is stuff that I wish prompt-toolkit just did by
  default (default emacs bindings). The main one I was annoyed wasn't properly
  extensible from prompt-toolkit's end was the word tokenization for
  forward-word, etc. Perhaps a good API would be to be able to pass in a
  function that takes the buffer text (or buffer object) and returns an
  iterator of word start and end positions, and maybe a custom wrapper that
  does this for you based on a regular expression that matches a word.

# Copied from ptpython

I copied and modified some stuff from ptpython. Some of this could be more extensible I'm
sure, but I also don't want to depend on ptpython, so I would have copied it
anyway.

- I copied `auto_newline` from ptpython, and modified it (it was missing some
  unindent keywords as I recall). I also originally copied ptpython's
  is_multiline_python stuff, but I have since rewritten it to do proper
  tokenization.

- I copied ptpython's jedi completion stuff. I cleaned it up a bit (replaced
  the redundant exceptions with a single `except Exception`, and added some
  completion code of my own based on Python's rlcompleter (I added code to the
  top of `PythonCompleter.get_completions`. I also deleted the Path completion
  stuff.

## Easy to extend (copying)

Things that were easy to extend, with some copying. I consider the
copy-pasting needed here to be just fine as far as extensibility.

- I started with prompt(), then worked my way out from it from the various
  shortcut functions, as I found various things that I wanted to do that I
  couldn't.

  The first was to copy the code from create_prompt_application directly to my
  program (ignoring the modularity and stuff I didn't care about), because I
  needed direct access to the cli object. My commit history says the original
  motivation for this was to get multiline inputs to work the way I wanted (it
  also says I did a similar thing to ptpython). At the present state, I need
  to do this for several reasons, such as the fact that I have a custom Buffer
  subclass.  I also see at least one keyword argument not present to
  create_prompt_application(), `tempfile_suffix`.

- At some point I may try to use a custom layout (instead of
  create_prompt_layout), to see if I can't fix
  https://github.com/jonathanslenders/python-prompt-toolkit/issues/493. From
  what I saw, if you want to change the layout even a little bit, you'd have
  to copy the entire create_prompt_layout() function (it's quite large) and
  modify it. I don't have much experience with GUI toolkits, so I can't say if
  there's a better way.

## Easy to extend (no copying)

Things I consider easy to extend. I did not need to copy-paste any code for these.

- My Buffer subclass also makes it so that the history search index resets
  when I type or delete text, so that I don't find myself in the middle of the search
  history when I don't want to be. This is achieved by defining
  `delete_before_cursor`, which resets the index and calls
  `super().delete_before_cursor()`, and by setting `on_text_insert` to the
  constructor. I noted at
  https://github.com/jonathanslenders/python-prompt-toolkit/issues/500 that an
  `on_text_deleted` hook would be nice.

## Cannot be extended

Some things that I don't see how to extend, or at least I haven't tried hard
enough yet.

- [Making it so that soft- and hard-wrapped text produce different continuation prompts](https://github.com/jonathanslenders/python-prompt-toolkit/issues/493).
  I think I could get this, or at least close to this (still not sure about
  not having the newlines in the text) by creating a custom layout, but that
  looks like a lot of code to copy, and I haven't attempted it yet.

- [Making completions work differently in terms of sync/async](https://github.com/jonathanslenders/python-prompt-toolkit/issues/497).
  The current completion framework is simultaneously too asynchronous and not
  asynchronous enough. You can't force text to block for a bit on completion
  (and there's no apparent way to indicate that there are no completions, as
  opposed to completions are still computing), and you can't get completions
  in parts, meaning it's pointless to add some "fast" completers on top of the
  often slow Jedi completer. I'm going to wait for this one to be fixed
  upstream, because I'm pretty sure I'd have to rewrite the completion
  framework from scratch to make it work the way I like.
