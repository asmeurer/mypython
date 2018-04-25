# Take from standard library rlcompleter module

# Changes:

# - Removed all readline specific stuff. Added logic to split words.

# - Renamed Completer to DirCompleter (for compatibility with
#   prompt_toolkit.Completer)

# - Removed _callable_postfix (code that adds '(' to the completions) because
#   I don't like it.

# - Made all completions case insensitive

# - Compile a regular expression

# - Prevent things like 1. from completing int attributes

# 1. This LICENSE AGREEMENT is between the Python Software Foundation ("PSF"), and
#    the Individual or Organization ("Licensee") accessing and otherwise using Python
#    3.6.0 software in source or binary form and its associated documentation.
#
# 2. Subject to the terms and conditions of this License Agreement, PSF hereby
#    grants Licensee a nonexclusive, royalty-free, world-wide license to reproduce,
#    analyze, test, perform and/or display publicly, prepare derivative works,
#    distribute, and otherwise use Python 3.6.0 alone or in any derivative
#    version, provided, however, that PSF's License Agreement and PSF's notice of
#    copyright, i.e., "Copyright © 2001-2017 Python Software Foundation; All Rights
#    Reserved" are retained in Python 3.6.0 alone or in any derivative version
#    prepared by Licensee.
#
# 3. In the event Licensee prepares a derivative work that is based on or
#    incorporates Python 3.6.0 or any part thereof, and wants to make the
#    derivative work available to others as provided herein, then Licensee hereby
#    agrees to include in any such work a brief summary of the changes made to Python
#    3.6.0.
#
# 4. PSF is making Python 3.6.0 available to Licensee on an "AS IS" basis.
#    PSF MAKES NO REPRESENTATIONS OR WARRANTIES, EXPRESS OR IMPLIED.  BY WAY OF
#    EXAMPLE, BUT NOT LIMITATION, PSF MAKES NO AND DISCLAIMS ANY REPRESENTATION OR
#    WARRANTY OF MERCHANTABILITY OR FITNESS FOR ANY PARTICULAR PURPOSE OR THAT THE
#    USE OF PYTHON 3.6.0 WILL NOT INFRINGE ANY THIRD PARTY RIGHTS.
#
# 5. PSF SHALL NOT BE LIABLE TO LICENSEE OR ANY OTHER USERS OF PYTHON 3.6.0
#    FOR ANY INCIDENTAL, SPECIAL, OR CONSEQUENTIAL DAMAGES OR LOSS AS A RESULT OF
#    MODIFYING, DISTRIBUTING, OR OTHERWISE USING PYTHON 3.6.0, OR ANY DERIVATIVE
#    THEREOF, EVEN IF ADVISED OF THE POSSIBILITY THEREOF.
#
# 6. This License Agreement will automatically terminate upon a material breach of
#    its terms and conditions.
#
# 7. Nothing in this License Agreement shall be deemed to create any relationship
#    of agency, partnership, or joint venture between PSF and Licensee.  This License
#    Agreement does not grant permission to use PSF trademarks or trade name in a
#    trademark sense to endorse or promote products or services of Licensee, or any
#    third party.
#
# 8. By copying, installing or otherwise using Python 3.6.0, Licensee agrees
#    to be bound by the terms and conditions of this License Agreement.


"""Word completion for GNU readline.

The completer completes keywords, built-ins and globals in a selectable
namespace (which defaults to __main__); when completing NAME.NAME..., it
evaluates (!) the expression up to the last dot and completes its attributes.

It's very cool to do "import sys" type "sys.", hit the completion key (twice),
and see the list of names defined by the sys module!

Tip: to use the tab key as the completion key, call

    readline.parse_and_bind("tab: complete")

Notes:

- Exceptions raised by the completer function are *ignored* (and generally cause
  the completion to fail).  This is a feature -- since readline sets the tty
  device in raw (or cbreak) mode, printing a traceback wouldn't work well
  without some complicated hoopla to save, reset and restore the tty state.

- The evaluation of the NAME.NAME... form may cause arbitrary application
  defined code to be executed if an object with a __getattr__ hook is found.
  Since it is the responsibility of the application (or the user) to enable this
  feature, I consider this an acceptable risk.  More complicated expressions
  (e.g. function calls or indexing operations) are *not* evaluated.

- When the original stdin is not a tty device, GNU readline is never
  used, and this module (and the readline module) are silently inactive.

"""
import re
import builtins
import __main__

__all__ = ["DirCompleter"]

class DirCompleter:
    def __init__(self, namespace = None):
        """Create a new completer for the command line.

        Completer([namespace]) -> completer instance.

        If unspecified, the default namespace where completions are performed
        is __main__ (technically, __main__.__dict__). Namespaces should be
        given as dictionaries.

        Completer instances should be used as the completion mechanism of
        readline via the set_completer() call:

        readline.set_completer(Completer(my_namespace).complete)
        """

        if namespace and not isinstance(namespace, dict):
            raise TypeError('namespace must be a dictionary')

        # Don't bind to namespace quite yet, but flag whether the user wants a
        # specific namespace or to use __main__.__dict__. This will allow us
        # to bind to __main__.__dict__ at completion time, not now.
        if namespace is None:
            self.use_main_ns = 1
        else:
            self.use_main_ns = 0
            self.namespace = namespace

    NAME = re.compile(r'[a-zA-Z0-9_\.]*[a-zA-Z_]')
    def complete(self, text, state):
        """Return the next possible completion for 'text'.

        This is called successively with state == 0, 1, 2, ... until it
        returns None.  The completion should begin with 'text'.

        """
        m = self.NAME.match(text[::-1])
        if not m:
            return None

        text = m.group(0)[::-1]
        if self.use_main_ns:
            self.namespace = __main__.__dict__

        if not text.strip():
            return None

        if state == 0:
            if "." in text:
                self.matches = self.attr_matches(text)
            else:
                self.matches = self.global_matches(text)
        try:
            return self.matches[state]
        except IndexError:
            return None

    def global_matches(self, text):
        """Compute matches when text is a simple name.

        Return a list of all keywords, built-in functions and names currently
        defined in self.namespace that match.

        """
        import keyword
        matches = []
        seen = {"__builtins__"}
        lower_text = text.lower()
        n = len(text)
        for word in keyword.kwlist:
            lower_word = word.lower()
            if lower_word[:n] == text:
                seen.add(word)
                if word in {'finally', 'try'}:
                    word = word + ':'
                elif word not in {'False', 'None', 'True',
                                  'break', 'continue', 'pass',
                                  'else'}:
                    word = word + ' '
                matches.append(word)
        for nspace in [self.namespace, builtins.__dict__]:
            for word, val in nspace.items():
                lower_word = word.lower()
                if lower_word[:n] == lower_text and word not in seen:
                    seen.add(word)
                    matches.append(word)
        return matches

    ATTRIBUTE = re.compile(r"(\w+(\.\w+)*)\.(\w*)")
    def attr_matches(self, text):
        """Compute matches when text contains a dot.

        Assuming the text is of the form NAME.NAME....[NAME], and is
        evaluable in self.namespace, it will be evaluated and its attributes
        (as revealed by dir()) are used as possible completions.  (For class
        instances, class members are also considered.)

        WARNING: this can still invoke arbitrary C code, if an object
        with a __getattr__ hook is evaluated.

        """
        m = self.ATTRIBUTE.match(text)
        if not m:
            return []
        expr, attr = m.group(1, 3)
        lower_attr = attr.lower()
        try:
            thisobject = eval(expr, self.namespace)
        except Exception:
            # Try to get a case insensitive version
            for i in self.namespace:
                if i.lower() == expr.lower():
                    expr = i
                    thisobject = eval(i, self.namespace)
                    break
            else:
                return []

        # get the content of the object, except __builtins__
        words = set(dir(thisobject))
        words.discard("__builtins__")

        if hasattr(thisobject, '__class__'):
            words.add('__class__')
            words.update(get_class_members(thisobject.__class__))
        matches = []
        n = len(attr)
        if attr == '':
            noprefix = '_'
        elif attr == '_':
            noprefix = '__'
        else:
            noprefix = None
        while True:
            for word in words:
                lower_word = word.lower()
                if (lower_word[:n] == lower_attr and
                    not (noprefix and word[:n+1] == noprefix)):
                    match = "%s.%s" % (expr, word)
                    try:
                        getattr(thisobject, word)
                    except Exception:
                        pass  # Include even if attribute not set
                    matches.append(match)
            if matches or not noprefix:
                break
            if noprefix == '_':
                noprefix = '__'
            else:
                noprefix = None
        matches.sort()
        return matches

def get_class_members(klass):
    ret = dir(klass)
    if hasattr(klass,'__bases__'):
        for base in klass.__bases__:
            ret = ret + get_class_members(base)
    return ret
