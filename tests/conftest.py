import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


def _has_python3(vim_bin):
    result = subprocess.run(
        [vim_bin, "-Nu", "NONE", "-nEs", "-c", "if !has('python3') | cquit | endif", "-c", "qa!"],
        check=False,
    )
    return result.returncode == 0


def run_headless_vim(script, python=False):
    """Run a Vim script in a headless Vim (or Neovim) with the repo as cwd.

    Pass python=True when the script needs Vim's Python 3 interface.
    """
    vim_bin = shutil.which("vim") or shutil.which("nvim")
    if vim_bin is None:
        pytest.skip("vim or nvim executable not available")
    if python and not _has_python3(vim_bin):
        pytest.skip(f"{vim_bin} has no Python 3 support")

    with tempfile.TemporaryDirectory() as tmpdir:
        script_path = Path(tmpdir) / "test.vim"
        script_path.write_text(script, encoding="utf-8")
        subprocess.run(
            [vim_bin, "-Nu", "NONE", "-nEs", "-S", str(script_path)],
            check=True,
            cwd=REPO_ROOT,
        )
