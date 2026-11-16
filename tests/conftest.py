import os
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


def run_headless_vim(script, python=False, timeout=60):
    """Run a Vim script in a headless Vim (or Neovim) with the repo as cwd.

    Pass python=True when the script needs Vim's Python 3 interface. Set
    VIM_AI_TEST_VIM to choose the editor binary (e.g. nvim).
    """
    vim_bin = os.environ.get("VIM_AI_TEST_VIM") or shutil.which("vim") or shutil.which("nvim")
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
            timeout=timeout,
            # py/*.py switch to pytest-style imports when PYTEST_VERSION is set
            env={k: v for k, v in os.environ.items() if k != "PYTEST_VERSION"},
        )
