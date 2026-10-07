import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]


def _find_vim():
    return shutil.which("vim") or shutil.which("nvim")


def _run_headless_vim(script):
    vim_bin = _find_vim()
    if vim_bin is None:
        pytest.skip("vim or nvim executable not available")

    with tempfile.TemporaryDirectory() as tmpdir:
        script_path = Path(tmpdir) / "test.vim"
        script_path.write_text(script, encoding="utf-8")
        subprocess.run(
            [vim_bin, "-Nu", "NONE", "-nEs", "-S", str(script_path)],
            check=True,
            cwd=REPO_ROOT,
        )


def test_latest_chat_bufnr_is_most_recently_used_unlisted_aichat():
    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = Path(tmpdir) / "result.txt"
        repo = str(REPO_ROOT).replace("'", "''")
        out = str(out_path).replace("'", "''")
        script = f"""
set nocompatible
set nomore
set hidden
set shortmess+=I
set rtp^={repo}

function! s:MakeChat(name) abort
  enew
  setlocal buftype=nofile noswapfile bufhidden=hide filetype=aichat nobuflisted
  execute 'file' fnameescape(a:name)
  return bufnr('%')
endfunction

let first = s:MakeChat('>>> AI chat')
sleep 1
let second = s:MakeChat('>>> AI chat 2')
sleep 1
execute 'buffer' first

try
  let got = vim_ai#GetLatestChatBufnr()
catch
  let got = 'ERROR: ' . v:exception
endtry
call writefile([string(first), string(second), string(got)], '{out}')
qa!
"""
        _run_headless_vim(script)

        first, second, got = out_path.read_text(encoding="utf-8").splitlines()
        assert got == first
        assert first != second


def test_open_latest_chat_splits_in_current_tab():
    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = Path(tmpdir) / "result.txt"
        repo = str(REPO_ROOT).replace("'", "''")
        out = str(out_path).replace("'", "''")
        script = f"""
set nocompatible
set nomore
set hidden
set shortmess+=I
set rtp^={repo}

enew
setlocal buftype=nofile noswapfile bufhidden=hide filetype=aichat nobuflisted
execute 'file' fnameescape('>>> AI chat')
let chat = bufnr('%')

enew
let dummy = bufnr('%')
let tabs_before = tabpagenr('$')

try
  let opened = vim_ai#OpenLatestChat()
catch
  let opened = 'ERROR: ' . v:exception
endtry
call writefile([
      \\ string(opened),
      \\ string(bufnr('%')),
      \\ string(chat),
      \\ string(dummy),
      \\ string(tabpagenr('$')),
      \\ string(tabs_before),
      \\ string(winnr('$')),
      \\ &filetype,
      \\], '{out}')
qa!
"""
        _run_headless_vim(script)

        opened, current, chat, dummy, tabs, tabs_before, windows, filetype = (
            out_path.read_text(encoding="utf-8").splitlines()
        )
        assert opened == "1"
        assert current == chat
        assert current != dummy
        assert tabs == tabs_before
        assert int(windows) >= 2
        assert filetype == "aichat"


def test_open_latest_chat_in_tab_shows_hidden_unlisted_buffer():
    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = Path(tmpdir) / "result.txt"
        repo = str(REPO_ROOT).replace("'", "''")
        out = str(out_path).replace("'", "''")
        script = f"""
set nocompatible
set nomore
set hidden
set shortmess+=I
set rtp^={repo}

enew
setlocal buftype=nofile noswapfile bufhidden=hide filetype=aichat nobuflisted
execute 'file' fnameescape('>>> AI chat')
let chat = bufnr('%')

enew
let dummy = bufnr('%')

try
  let opened = vim_ai#OpenLatestChatInTab()
catch
  let opened = 'ERROR: ' . v:exception
endtry
call writefile([
      \\ string(opened),
      \\ string(bufnr('%')),
      \\ string(chat),
      \\ string(dummy),
      \\ string(tabpagenr('$')),
      \\ &filetype,
      \\], '{out}')
qa!
"""
        _run_headless_vim(script)

        opened, current, chat, dummy, tabs, filetype = out_path.read_text(
            encoding="utf-8"
        ).splitlines()
        assert opened == "1"
        assert current == chat
        assert current != dummy
        assert int(tabs) >= 2
        assert filetype == "aichat"
