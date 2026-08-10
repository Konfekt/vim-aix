from unittest.mock import MagicMock, patch

from providers.openai import OpenAIProvider


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
    with patch('providers.openai.vim.eval', side_effect=lambda cmd: defaults if cmd == 'g:vim_ai_openai_chat' else None):
        return OpenAIProvider('chat', raw_options, MagicMock())


def test_chat_completions_maps_max_reasoning_effort_to_xhigh():
    provider = _provider({'reasoning_effort': 'max'})
    result = provider._make_openai_options(provider.options)
    assert result['reasoning_effort'] == 'xhigh'
    assert result['model'] == 'gpt-5.6-luna'
