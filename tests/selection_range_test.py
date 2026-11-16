import json
import tempfile
from pathlib import Path

from conftest import REPO_ROOT, run_headless_vim


def test_visual_selection_detection_does_not_leak_into_explicit_ranges():
    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = Path(tmpdir) / "result.txt"
        repo = str(REPO_ROOT).replace("'", "''")
        out = str(out_path).replace("'", "''")
        script = f"""
set nocompatible
set nomore
set shortmess+=I
set rtp^={repo}
call vim_ai#AIUtilSetDebug(0)

new
call setline(1, ['Lorem ipsum dolor sit amet.'])
call setpos("'<", [0, 1, 1, 0])
call setpos("'>", [0, 1, 5, 0])

let explicit_range_result = vim_ai#IsVisualSelectionRange(1, 1, 1, '.Probe')

let visual_range_result = vim_ai#IsVisualSelectionRange(1, 1, 1, "'<,'>Probe")

call writefile([string(explicit_range_result), string(visual_range_result)], '{out}')
qa!
"""
        run_headless_vim(script)

        results = out_path.read_text(encoding="utf-8").splitlines()
        assert results == ["0", "1"]


def test_redo_preserves_explicit_range_for_image_commands():
    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = Path(tmpdir) / "result.txt"
        repo = str(REPO_ROOT).replace("'", "''")
        out = str(out_path).replace("'", "''")
        script = f"""
set nocompatible
set nomore
set shortmess+=I
set rtp^={repo}
call vim_ai#AIUtilSetDebug(0)

py3 << PY
import json
from pathlib import Path
import vim
records = []
for name in ['types', 'utils', 'context', 'chat', 'complete', 'roles', 'image']:
    globals()[f'{{name}}_py_imported'] = True

def unwrap(expr):
    return vim.eval(expr)

def make_ai_context(config_input):
    records.append({{
        'user_selection': config_input['user_selection'],
        'is_selection': config_input['is_selection'],
        'command_type': config_input['command_type'],
    }})
    return {{'config': {{'ui': {{'paste_mode': '0'}}}}, 'prompt': ''}}

def run_ai_image(context):
    pass
PY

new
call setline(1, ['abcdef', 'ghijkl'])
1,1call vim_ai#AIImageRun(2, {{}}, '')
normal! G
call vim_ai#AIRedoRun()
py3 Path('{out}').write_text(json.dumps(records), encoding='utf-8')
qa!
"""
        run_headless_vim(script, python=True)

        results = json.loads(out_path.read_text(encoding="utf-8"))
        assert results == [
            {
                "user_selection": "abcdef",
                "is_selection": "0",
                "command_type": "image",
            },
            {
                "user_selection": "abcdef",
                "is_selection": "0",
                "command_type": "image",
            },
        ]


_MOCK_PYTHON = """
py3 << PY
import json
from pathlib import Path
import vim
records = []
for name in ['types', 'utils', 'context', 'chat', 'complete', 'roles', 'image']:
    globals()[f'{name}_py_imported'] = True

def unwrap(expr):
    return vim.eval(expr)

def make_ai_context(config_input):
    records.append(config_input['user_selection'])
    return {'config': {'ui': {'paste_mode': '0'}}, 'prompt': ''}

def run_ai_image(context):
    pass

def load_ai_role_names(command_type):
    return ['grammar', 'c++', 'quo"te']
PY
"""


def test_visual_selection_keeps_multibyte_last_character():
    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = Path(tmpdir) / "result.txt"
        repo = str(REPO_ROOT).replace("'", "''")
        out = str(out_path).replace("'", "''")
        script = f"""
set nocompatible
set nomore
set encoding=utf-8
set rtp^={repo}
call vim_ai#AIUtilSetDebug(0)
{_MOCK_PYTHON}
new
call setline(1, ['xäöüy'])
" select äöü (byte columns 2 to 6)
call setpos("'<", [0, 1, 2, 0])
call setpos("'>", [0, 1, 6, 0])
call histadd(':', "'<,'>AIImage")
1,1call vim_ai#AIImageRun(2, {{}}, '')
py3 Path('{out}').write_text(json.dumps(records), encoding='utf-8')
qa!
"""
        run_headless_vim(script, python=True)

        assert json.loads(out_path.read_text(encoding="utf-8")) == ["äöü"]


def test_role_completion_matches_literal_prefix():
    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = Path(tmpdir) / "result.txt"
        repo = str(REPO_ROOT).replace("'", "''")
        out = str(out_path).replace("'", "''")
        script = f"""
set nocompatible
set nomore
set encoding=utf-8
set rtp^={repo}
{_MOCK_PYTHON}
let results = {{}}
for prefix in ['/', '/c+', '/quo"', '/.', 'grammar']
  let results[prefix] = vim_ai#RoleCompletionChat(prefix, '', 0)
endfor
call writefile([json_encode(results)], '{out}')
qa!
"""
        run_headless_vim(script, python=True)

        assert json.loads(out_path.read_text(encoding="utf-8")) == {
            "/": ["/grammar", "/c++", '/quo"te'],
            "/c+": ["/c++"],
            '/quo"': ['/quo"te'],
            "/.": [],
            "grammar": [],
        }
