import builtins
import linecache
import os
import types

import pytest

from ..memory_profiler import register_source, run_memory_profiler
from ..line_profiler import run_line_profiler


class _MemoryCodeMap:
    def add(self, compiled):
        pass


class _MemoryLineProfiler:
    def __init__(self):
        self.code_map = _MemoryCodeMap()

    def add_function(self, func):
        pass

    def runctx(self, compiled, globals, locals):
        exec(compiled, globals, locals)


class _LineProfiler:
    def __init__(self, *funcs):
        pass

    def add_module(self, mod):
        pass

    def runctx(self, compiled, globals, locals):
        exec(compiled, globals, locals)

    def print_stats(self, stream, stripzeros=True):
        stream.write("line stats\n")


def _show_memory_results(profile, stream, precision=1):
    stream.write("memory stats\n")


@pytest.fixture
def fake_profiler_modules(monkeypatch):
    monkeypatch.setitem(
        os.sys.modules,
        "memory_profiler",
        types.SimpleNamespace(
            LineProfiler=_MemoryLineProfiler,
            show_results=_show_memory_results,
        ),
    )
    monkeypatch.setitem(
        os.sys.modules,
        "line_profiler",
        types.SimpleNamespace(LineProfiler=_LineProfiler),
    )


def test_register_source_unlinks_temp_file_on_compile_error(tmp_path,
                                                           monkeypatch):
    temp_source = tmp_path / "bad-source.py"

    def mkstemp(prefix, suffix):
        fd = os.open(temp_source, os.O_RDWR | os.O_CREAT | os.O_EXCL)
        return fd, str(temp_source)

    monkeypatch.setattr("tempfile.mkstemp", mkstemp)

    with pytest.raises(SyntaxError):
        register_source("def f(:\n    pass\n", "test")

    assert not temp_source.exists()
    assert str(temp_source) not in linecache.cache


def test_memory_profiler_deletes_injected_builtin(fake_profiler_modules,
                                                  monkeypatch):
    monkeypatch.delitem(builtins.__dict__, "profile", raising=False)

    assert run_memory_profiler("x = 1", {}, {}) == "memory stats"

    assert "profile" not in builtins.__dict__


def test_memory_profiler_restores_builtin_after_compile_error(
        fake_profiler_modules, monkeypatch):
    old_profile = object()
    monkeypatch.setitem(builtins.__dict__, "profile", old_profile)

    with pytest.raises(SyntaxError):
        run_memory_profiler("def f(:\n    pass\n", {}, {})

    assert builtins.__dict__["profile"] is old_profile


def test_line_profiler_deletes_injected_builtin(fake_profiler_modules,
                                                monkeypatch):
    monkeypatch.delitem(builtins.__dict__, "profile", raising=False)

    assert run_line_profiler("x = 1", {}, {}) == "line stats"

    assert "profile" not in builtins.__dict__


def test_line_profiler_restores_builtin_after_compile_error(
        fake_profiler_modules, monkeypatch):
    old_profile = object()
    monkeypatch.setitem(builtins.__dict__, "profile", old_profile)

    with pytest.raises(SyntaxError):
        run_line_profiler("def f(:\n    pass\n", {}, {})

    assert builtins.__dict__["profile"] is old_profile
