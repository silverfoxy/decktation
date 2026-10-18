"""The Gamescope helper must reject invalid payloads without a compositor."""
from pathlib import Path
import subprocess
import pytest


@pytest.fixture(scope="module")
def helper(tmp_path_factory):
    root = Path(__file__).resolve().parents[1]
    source = root / "backend" / "src"
    protocol = source / "gamescope-input-method.xml"
    out = tmp_path_factory.mktemp("gamescope-helper")
    header = out / "gamescope-input-method-client-protocol.h"
    code = out / "gamescope-input-method-protocol.c"
    subprocess.run(["wayland-scanner", "client-header", str(protocol), str(header)], check=True)
    subprocess.run(["wayland-scanner", "private-code", str(protocol), str(code)], check=True)
    binary = out / "gamescope-inject"
    subprocess.run(["cc", "-std=c11", "-O2", "-Wall", "-Wextra", "-Werror", "-I", str(out),
                    str(source / "gamescope_inject.c"), str(code), "-lwayland-client", "-o", str(binary)], check=True)
    return binary


@pytest.mark.parametrize("payload", [b"bad\x00text", b"bad\ntext", b"\xff", b"\xc0\xaf", b"\xed\xa0\x80", b"\xf4\x90\x80\x80", b"x" * 41, b"x" * 4097])
def test_rejects_invalid_text_before_connecting(helper, payload, tmp_path):
    result = subprocess.run([str(helper)], input=payload, env={"XDG_RUNTIME_DIR": str(tmp_path)}, capture_output=True, timeout=3)
    assert result.returncode != 0
    assert b"Invalid text" in result.stderr
    assert payload not in result.stderr


def test_valid_utf8_reaches_gamescope_connection_attempt(helper, tmp_path):
    for payload in ["mañana Привет".encode(), b"x" * 40, "😀".encode() * 40]:
        result = subprocess.run([str(helper)], input=payload,
                                env={"XDG_RUNTIME_DIR": str(tmp_path)}, capture_output=True, timeout=3)
        assert result.returncode != 0
        assert b"Gamescope socket unavailable" in result.stderr


def test_helper_retains_gamescope_keymap_after_commit():
    """Static guard: the pinned compositor resets temporary keymaps after 100 ms."""
    source = (Path(__file__).resolve().parents[1] / "backend" / "src" / "gamescope_inject.c").read_text()
    commit = source.index("gamescope_input_method_commit(ime, ctx.serial)")
    close = source.index("gamescope_input_method_destroy(ime)")
    assert "nanosleep(" in source[commit:close]


def test_probe_reports_no_gamescope_without_hanging(helper, tmp_path):
    result = subprocess.run([str(helper), "--probe"], env={"XDG_RUNTIME_DIR": str(tmp_path)}, capture_output=True, timeout=3)
    assert result.returncode != 0
