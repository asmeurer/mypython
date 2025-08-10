# can_print_sympy modified from _can_print_latex taken from sympy.interactive.printing

# Copyright (c) 2006-2017 SymPy Development Team
#
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   a. Redistributions of source code must retain the above copyright notice,
#      this list of conditions and the following disclaimer.
#   b. Redistributions in binary form must reproduce the above copyright
#      notice, this list of conditions and the following disclaimer in the
#      documentation and/or other materials provided with the distribution.
#   c. Neither the name of SymPy nor the names of its contributors
#      may be used to endorse or promote products derived from this software
#      without specific prior written permission.
#
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE REGENTS OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY
# OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH
# DAMAGE.
#


import sys
from io import BytesIO

try:
    from iterm2_tools import display_image_bytes
except ImportError:
    import platform
    if platform.system() == "Darwin":
        raise
    display_image_bytes = lambda x: ''

from . import mypython

def can_print_sympy(o):
    """Return True if type o can be printed with sympy.pretty.

    If o is a container type, this is True if and only if every element of
    o can be printed with SymPy.
    """
    from sympy import Basic
    from sympy.matrices import MatrixBase
    from sympy.physics.vector import Vector, Dyadic
    try:
        from sympy.tensor.array import NDimArray
    except ImportError:
        # Support older versions of SymPy
        NDimArray = Basic

    try:
        builtin_types = (list, tuple, set, frozenset)
        if isinstance(o, builtin_types):
            # If the object is a custom subclass with a custom str or
            # repr, use that instead.
            if (type(o).__str__ not in (i.__str__ for i in builtin_types) or
                type(o).__repr__ not in (i.__repr__ for i in builtin_types)):
                return False
            return all(can_print_sympy(i) for i in o)
        elif isinstance(o, dict):
            return all(can_print_sympy(i) and can_print_sympy(o[i]) for i in o)
        elif isinstance(o, bool):
            return False
        elif isinstance(o, (Basic, MatrixBase, Vector, Dyadic, NDimArray)):
            return True
        elif isinstance(o, (int, float)):
            return False
        return False
    except RecursionError:
        return False

def mypython_displayhook(value):
    """
    Unlike the default displayhook:

    - doesn't set builtins._ (we do that separately),
    - always prints None,
    - prints a newline before a multiline output, so the out prompt doesn't
      mess up pretty printing,
    - uses sympy.pretty() for SymPy objects.

    """
    if value is mypython.NoResult:
        return

    sympy = sys.modules.get('sympy', None)

    if not mypython.DOCTEST_MODE and sympy and can_print_sympy(value):
        res = sympy.pretty(value, use_unicode=True)
    else:
        res = repr(value)

    if not mypython.DOCTEST_MODE and '\n' in res:
        # Print multiline stuff below the out prompt
        print()
    print(res)

def latex_in_terminal(expr):
    from sympy import preview

    obj = BytesIO()
    preamble = r'''
\documentclass[6pt]{article}
\usepackage{amsmath,amsfonts}
\pagestyle{empty}
\begin{document}
'''
    dvioptions = ["-T", "tight", "--truecolor", '-fg', 'Green', '-bg', 'Transparent', '-D', '150']
    preview(expr, euler=False, output='png', viewer='BytesIO',
        outputbuffer=obj, preamble=preamble, dvioptions=dvioptions,
        # Setting the mode only works in my sympy branch
        # mode='equation*',
        )
    print(display_image_bytes(obj.getvalue()))
