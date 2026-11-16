import tempfile
from pathlib import Path

from conftest import REPO_ROOT, run_headless_vim

_PRELUDE = """
set nocompatible
set nomore
set hidden
set shortmess+=I
set rtp^=@REPO@
@SETUP@
call vim_ai#AIUtilSetDebug(0)

function! SFunc(name) abort
  let l:sid = matchstr(execute('scriptnames'), '\\v(\\d+)\\ze: \\S*autoload[/\\\\]vim_ai\\.vim')
  return function('<SNR>' . l:sid . '_' . a:name)
endfunction
"""


def _run(body, python=False, timeout=60, setup=""):
    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = Path(tmpdir) / "result.txt"
        repo = str(REPO_ROOT).replace("'", "''")
        script = (_PRELUDE + body).replace("@SETUP@", setup).replace("@REPO@", repo).replace("@OUT@", str(out_path).replace("'", "''"))
        run_headless_vim(script, python=python, timeout=timeout)
        return out_path.read_text(encoding="utf-8").splitlines()


def test_reusing_kept_open_chat_with_plain_split_keeps_user_buffer():
    results = _run("""
let g:vim_ai_chat = {'ui': {'scratch_buffer_keep_open': 1}}
enew
setlocal buftype=nofile noswapfile bufhidden=hide filetype=aichat
file >>>\\ AI\\ chat
let chat = bufnr('%')
enew
call setline(1, 'user text')
file user.txt
let user = bufnr('%')
call SFunc('OpenChatWindow')('split', 0)
call writefile([
      \\ string(bufexists(user)),
      \\ string(bufnr('%') == chat),
      \\ string(winnr('$')),
      \\ string(win_findbuf(user) != []),
      \\ ], '@OUT@')
qa!
""")
    assert results == ["1", "1", "2", "1"]


def test_reusing_kept_open_chat_wipes_placeholder_buffer():
    results = _run("""
let g:vim_ai_chat = {'ui': {'scratch_buffer_keep_open': 1}}
enew
setlocal buftype=nofile noswapfile bufhidden=hide filetype=aichat
file >>>\\ AI\\ chat
let chat = bufnr('%')
enew
file user.txt
let before = len(getbufinfo())
call SFunc('OpenChatWindow')('below new', 0)
call writefile([string(bufnr('%') == chat), string(len(getbufinfo()) - before)], '@OUT@')
qa!
""")
    assert results == ["1", "0"]


def test_redo_without_previous_command_does_not_undo_user_change():
    results = _run("""
new
call setline(1, 'first')
let &undolevels = &undolevels
call feedkeys("Achanged\\<Esc>", 'xt')
silent! call vim_ai#AIRedoRun()
call writefile([getline(1)], '@OUT@')
qa!
""")
    assert results == ["firstchanged"]


def test_user_config_does_not_mutate_default_config():
    results = _run(setup="let g:vim_ai_chat = {'ui': {'open_chat_command': 'preset_tab'}}", body="""
call writefile([g:vim_ai_chat.ui.open_chat_command, g:vim_ai_chat_default.ui.open_chat_command], '@OUT@')
qa!
""")
    assert results == ["preset_tab", "preset_below"]


def test_undo_cleanup_terminates_when_undo_history_is_too_short():
    results = _run("""
py3 << PY
for name in ['types', 'utils', 'context', 'chat', 'complete', 'roles', 'image']:
    globals()[name + '_py_imported'] = True

class _Pool:
    def is_job_done(self, bufnr):
        return True

ai_job_pool = _Pool()

def unwrap(expr):
    import vim
    return vim.eval(expr)
PY
new
set undolevels=-1
call setline(1, ['>>> user', '', 'question'])
let b:vim_ai_chat_start_last_line = 3
call append('$', ['', '<<< assistant', '', 'answer 1'])
call append('$', ['answer 2'])
call SFunc('AIChatUndoCleanup')()
call writefile([string(line('$')), getline('$'), string(b:vim_ai_chat_start_last_line)], '@OUT@')
qa!
""", python=True, timeout=20)
    assert results == ["8", "answer 2", "-1"]


def test_sync_chat_error_names_the_provider():
    results = _run(setup="""
let g:vim_ai_chat = {'provider': 'failing'}
let g:vim_ai_async_chat = 0
""", body="""
call vim_ai_provider#Register('failing', {
      \\ 'script_path': '@REPO@/tests/resources/providers/failing.py',
      \\ 'class_name': 'FailingProvider',
      \\ })
call vim_ai#AIChatRun(0, {}, 'hello')
call writefile(split(execute('messages'), "\\n"), '@OUT@')
qa!
""", python=True)
    assert "failing: HTTPError 401" in results
