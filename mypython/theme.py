"""
Based on https://github.com/asmeurer/dotfiles/blob/master/.emacs.d/themes/1am-theme.el

Translated from http://raebear.net/comp/emacscolors.html
"""
from collections import OrderedDict
from itertools import cycle

from pygments.token import Keyword, Name, Comment, String, Operator, Text
from pygments.style import Style
from pygments.lexers import Python3Lexer

from .magic import MAGICS

class MyPython3Lexer(Python3Lexer):
    def get_tokens_unprocessed(self, text):
        magic = False
        first = True
        prev = None
        for index, token, value in \
            super().get_tokens_unprocessed(text):
            if magic:
                magic = False
                if token is Name and value in [i[1:] for i in MAGICS]:
                    for i, color in zip('%' + value, cycle(rainbow)):
                        yield index, color, i
                    prev = None
                    continue
                else:
                    yield prev
                    prev = None
            if first and token is Operator and value == '%':
                magic = True
                prev = index, token, value
                continue
            yield index, token, value
            first = False

        if prev:
            yield prev

rainbow = OrderedDict([
    (Text.Red, "#ff0000"),
    (Text.Orange, "#ffa500"),
    (Text.Yellow, "#ffff00"),
    (Text.Green, "#00ff00"),
    (Text.Blue, "#0000ff"),
    (Text.Indigo, "#4b0082"),
    (Text.Violet, "#ee82ee"),
    ])

class OneAMStyle(Style):
    default_style = ''
    styles = {
        String:              "#ff0000", # red
        String.Doc:          "#ffff00", # yellow
        Comment:             "#ffffff", # white
        Keyword:             "#a020f0", # purple
        Operator.Word:       "#a020f0", # purple
        # Doesn't work for some reason. Should highlight True, False, and
        # None.
        Keyword.Constant:    "#008b8b", # dark cyan
        Name.Builtin:        "#483d8b", # dark slate blue
        Name.Function:       "#0000ff", # Blue1
        Name.Class:          "#228b22", # ForestGreen
        Name.Exception:      "#228b22", # ForestGreen
        Name.Decorator:      "#228b22", # ForestGreen
        # Doesn't work
        Name.Variable:       "#a0522d", # sienna
        **rainbow,
    }

# Uncomment this to register the style with pygments
#
# from pygments.styles import STYLE_MAP
#
# import sys
#
# STYLE_MAP['OneAM'] = 'OneAM::OneAMStyle'
# sys.modules['pygments.styles.OneAM'] = sys.modules['mypython.theme']
