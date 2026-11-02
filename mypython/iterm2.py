"""
iTerm2 terminal sequences: shell integration and inline images.

See https://iterm2.com/documentation-escape-codes.html and
https://iterm2.com/documentation-images.html for the sequences, and
https://iterm2.com/documentation-shell-integration.html for what shell
integration enables.

Notes about how iTerm2 treats the shell integration sequences:

- The text after the prompt and before the first newline is read as the
  command. If it is empty or only whitespace, the output is effectively
  ignored, as if there were no output sequences at all.

- Multiline commands can't be captured, but the output won't include any part
  of the command as long as BEFORE_OUTPUT is emitted correctly.

- There should be nothing between AFTER_OUTPUT and BEFORE_PROMPT except possibly
  more sequences. "Select Output of Last Command" actually selects the text
  between BEFORE_OUTPUT and BEFORE_PROMPT, not BEFORE_OUTPUT and AFTER_OUTPUT.

- Multiline prompts work, although the arrow is always shown on the first line.
  Don't try to change this by leaving part of the prompt outside of the prompt
  sequences (see the previous point).
"""
import base64
import sys

# The "FinalTerm" shell sequences

BEFORE_PROMPT = '\033]133;A\a'
AFTER_PROMPT = '\033]133;B\a'
BEFORE_OUTPUT = '\033]133;C\a'
AFTER_OUTPUT = '\033]133;D;{command_status}\a'

IMAGE = '\033]1337;File=inline=1;size={size}:{data}\a'

class Output:
    """
    Context manager that marks everything printed inside of it as the output
    of a command.

    Use like::

        with Output() as o:
            print("output")
            o.set_command_status(1)

    The default command status is 0.
    """
    def __init__(self):
        self.command_status = 0

    def set_command_status(self, status):
        if status not in range(256):
            raise ValueError("status must be an integer in the range 0-255")
        self.command_status = status

    # Flushing is important in both of these, as iTerm2's command timing is
    # based on when it receives the sequences.
    def __enter__(self):
        sys.stdout.write(BEFORE_OUTPUT)
        sys.stdout.flush()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        sys.stdout.write(AFTER_OUTPUT.format(command_status=self.command_status))
        sys.stdout.flush()

def image_sequence(b):
    """
    Return the string that displays the image with the bytes b inline when it
    is printed to the terminal.
    """
    return IMAGE.format(size=len(b), data=base64.b64encode(b).decode('ascii'))
