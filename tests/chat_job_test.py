from unittest.mock import MagicMock

import utils
from utils import *  # noqa: F401,F403 - chat.py expects utils in its namespace
import importlib.util
import os

PY_DIR = os.path.join(os.path.dirname(__file__), '..', 'py')


def _load_chat_module():
    spec = importlib.util.spec_from_file_location('vim_ai_chat', os.path.join(PY_DIR, 'chat.py'))
    module = importlib.util.module_from_spec(spec)
    module.__dict__.update({k: v for k, v in vars(utils).items() if not k.startswith('__')})
    spec.loader.exec_module(module)
    return module


chat = _load_chat_module()


def test_chat_job_flushes_partial_line_before_error_report():
    def failing_request(messages):
        yield {'type': 'assistant', 'content': 'partial answer'}
        raise RuntimeError('connection lost')

    provider = MagicMock()
    provider.request = failing_request
    job = chat.AI_chat_job({'bufnr': 1}, [], provider)
    job.run()
    lines = job.pickup_lines()
    partial = lines.index('partial answer')
    error = next(i for i, line in enumerate(lines) if line.startswith('<<< error getting response'))
    assert partial < error
