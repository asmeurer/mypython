"""
line_profiler extension

Based on the line_profiler ipython extension
https://github.com/pyutils/line_profiler/blob/main/line_profiler/ipython_extension.py

This software is OSI Certified Open Source Software.
OSI Certified is a certification mark of the Open Source Initiative.

Copyright (c) 2008, Enthought, Inc.
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

 * Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.
 * Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.
 * Neither the name of Enthought, Inc. nor the names of its contributors may
   be used to endorse or promote products derived from this software without
   specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

from io import StringIO

def run_line_profiler(code, globals, locals, *, funcs=(), modules=(),
                      add_to_builtins=True, stripzeros=True):
    from line_profiler import LineProfiler

    profile = LineProfiler(*funcs)

    for mod in modules:
        profile.add_module(mod)

    if add_to_builtins:
        # Add the profiler to the builtins for @profile.
        import builtins

        if "profile" in builtins.__dict__:
            had_profile = True
            old_profile = builtins.__dict__["profile"]
        else:
            had_profile = False
            old_profile = None
        builtins.__dict__["profile"] = profile

    try:
        try:
            profile.runctx(code, globals, locals)
            message = ""
        except SystemExit:
            message = """*** SystemExit exception caught in code being profiled."""
        except KeyboardInterrupt:
            message = (
                "*** KeyboardInterrupt exception caught in code being " "profiled."
            )
    finally:
        if add_to_builtins and had_profile:
            builtins.__dict__["profile"] = old_profile

    # Trap text output.
    stdout_trap = StringIO()
    profile.print_stats(stdout_trap, stripzeros=stripzeros)
    output = stdout_trap.getvalue()
    output = output.rstrip()

    return output
