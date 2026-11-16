import importlib.util
import os
from unittest.mock import MagicMock, patch

PY_DIR = os.path.join(os.path.dirname(__file__), '..', 'py')


def _load_openai_module():
    # Vim loads py/types.py and the provider with :py3file into one shared
    # namespace, so the provider's annotations can use the types unqualified.
    # Mirror that here (needed on Python < 3.14, which evaluates annotations
    # eagerly).
    types_spec = importlib.util.spec_from_file_location('vim_ai_types', os.path.join(PY_DIR, 'types.py'))
    types_module = importlib.util.module_from_spec(types_spec)
    types_spec.loader.exec_module(types_module)

    spec = importlib.util.spec_from_file_location('vim_ai_openai', os.path.join(PY_DIR, 'providers', 'openai.py'))
    module = importlib.util.module_from_spec(spec)
    module.__dict__.update({k: v for k, v in vars(types_module).items() if k.startswith('AI')})
    spec.loader.exec_module(module)
    return module


openai = _load_openai_module()
OpenAIProvider = openai.OpenAIProvider


def _openai_chat_defaults():
    return {
        'model': 'gpt-5.6-luna',
        'endpoint_url': 'https://api.openai.com/v1/chat/completions',
        'max_tokens': 0,
        'max_completion_tokens': 0,
        'temperature': 1,
        'request_timeout': 20,
        'stream': 1,
        'auth_type': 'bearer',
        'token_file_path': '',
        'token_load_fn': '',
        'selection_boundary': '',
        'initial_prompt': '',
        'frequency_penalty': '',
        'logit_bias': '',
        'logprobs': '',
        'presence_penalty': '',
        'reasoning_effort': '',
        'seed': '',
        'stop': '',
        'top_logprobs': '',
        'top_p': '',
        'reasoning': '',
    }


def _provider(raw_options):
    defaults = _openai_chat_defaults()
    with patch.object(openai.vim, 'eval', side_effect=lambda cmd: defaults if cmd == 'g:vim_ai_openai_chat' else None):
        return OpenAIProvider('chat', raw_options, MagicMock())


def test_chat_completions_maps_max_reasoning_effort_to_xhigh():
    provider = _provider({'reasoning_effort': 'max'})
    result = provider._make_openai_options(provider.options)
    assert result['reasoning_effort'] == 'xhigh'
    assert result['model'] == 'gpt-5.6-luna'


def test_chat_completions_keeps_supported_reasoning_effort():
    provider = _provider({'reasoning_effort': 'high'})
    result = provider._make_openai_options(provider.options)
    assert result['reasoning_effort'] == 'high'


def test_responses_endpoint_keeps_max_reasoning_effort():
    provider = _provider({'reasoning_effort': 'max', 'endpoint_url': 'https://api.openai.com/v1/responses'})
    result = provider._make_openai_options(provider.options)
    assert result['reasoning_effort'] == 'max'


class _FakeResponse:
    def __init__(self, lines):
        self.lines = lines

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def __iter__(self):
        return iter(self.lines)


def test_stream_parses_last_event_without_trailing_newline():
    provider = _provider({'auth_type': 'none'})
    provider.utils.get_proxy_settings.return_value = None
    lines = [
        b'data: {"choices": [{"delta": {"content": "a"}}]}\r\n',
        b'\n',
        b'data: \n',
        b'data: {"choices": [{"delta": {"content": "b"}}]}',
    ]
    with patch.object(openai.urllib.request, 'urlopen', return_value=_FakeResponse(lines)):
        chunks = list(provider.request([{'role': 'user', 'content': [{'type': 'text', 'text': 'hi'}]}]))
    assert [c['content'] for c in chunks] == ['a', 'b']


def test_stream_stops_at_done_marker():
    provider = _provider({'auth_type': 'none'})
    provider.utils.get_proxy_settings.return_value = None
    lines = [
        b'data: {"choices": [{"delta": {"content": "a"}}]}\n',
        b'data: [DONE]\n',
        b'data: not json\n',
    ]
    with patch.object(openai.urllib.request, 'urlopen', return_value=_FakeResponse(lines)):
        chunks = list(provider.request([{'role': 'user', 'content': [{'type': 'text', 'text': 'hi'}]}]))
    assert [c['content'] for c in chunks] == ['a']
