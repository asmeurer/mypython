"""
memory_profiler extension

Based on the memory_profiler ipython extension
https://github.com/pythonprofilers/memory_profiler/blob/master/memory_profiler.py

memory_profiler is licensed under the Simplified BSD License:

Copyright (c) 2007-2014 Fabian Pedregosa.
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

 * Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.
 * Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

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

import inspect
import linecache
import os
import tempfile
import builtins
from io import StringIO

def register_source(code, prefix):
    """
    Write code to a temporary file and compile it with that filename.

    The profilers require the profiled code to live in a real file to show
    source lines (memory_profiler checks os.path.exists on the filename).
    The source is also registered in linecache so that tracebacks can show it
    even after the file is deleted.

    Returns (compiled code object, filename). The caller is responsible for
    deleting the file when done with it.
    """
    fd, filename = tempfile.mkstemp(prefix='mypython-%s-' % prefix,
                                    suffix='.py')
    with os.fdopen(fd, 'w') as f:
        f.write(code)
    linecache.cache[filename] = (len(code), None, code.splitlines(True),
                                 filename)
    try:
        compiled = compile(code, filename, 'exec')
    except Exception:
        linecache.cache.pop(filename, None)
        os.unlink(filename)
        raise
    return compiled, filename

def run_memory_profiler(code, globals, locals, *, funcs=(), modules=(),
                        add_to_builtins=True, precision=1):
    from memory_profiler import LineProfiler, show_results

    profile = LineProfiler()
    filename = None
    had_profile = False
    old_profile = None

    try:
        for func in funcs:
            profile.add_function(func)

        for mod in modules:
            for _, member in inspect.getmembers(mod, inspect.isfunction):
                profile.add_function(member)

        if add_to_builtins:
            # Add the profiler to the builtins for @profile.
            if "profile" in builtins.__dict__:
                had_profile = True
                old_profile = builtins.__dict__["profile"]
            builtins.__dict__["profile"] = profile

        compiled, filename = register_source(code, 'memory-profiler')

        # Profile the code itself, including any functions defined in it
        # (code_map.add recursively adds nested code objects), so that @profile
        # is not required.
        profile.code_map.add(compiled)

        try:
            profile.runctx(compiled, globals, locals)
            message = ""
        except SystemExit:
            message = """*** SystemExit exception caught in code being profiled."""
        except KeyboardInterrupt:
            message = (
                "*** KeyboardInterrupt exception caught in code being " "profiled."
            )

        # Trap text output.
        stdout_trap = StringIO()
        show_results(profile, stdout_trap, precision=precision)
        output = stdout_trap.getvalue()
        output = output.rstrip()
    finally:
        if add_to_builtins:
            if had_profile:
                builtins.__dict__["profile"] = old_profile
            else:
                builtins.__dict__.pop("profile", None)
        if filename is not None:
            os.unlink(filename)

    if message:
        output = message + "\n" + output

    return output
