import os
from utils import (
    KnownError,
    _parse_llm_template_file,
    _parse_markdown_role_file,
    ai_provider_utils,
    enhance_roles_with_custom_function,
    is_image_path,
    make_exec_output_message,
    parse_include_paths,
)
import pytest
import vim
from unittest.mock import patch

dirname = os.path.dirname(__file__)
root_dir = os.path.abspath(os.path.join(dirname, '..'))

def test_parse_relative_path():
    actual = parse_include_paths('tests/resources/test1.include.txt')
    assert ['tests/resources/test1.include.txt'] == actual

def test_parse_absolute_path():
    actual = parse_include_paths(f'{root_dir}/tests/resources/test1.include.txt')
    assert [f'{root_dir}/tests/resources/test1.include.txt'] == actual

def test_parse_relative_path_glob():
    actual = parse_include_paths('**/*.include.txt')
    assert [
        'tests/resources/test1.include.txt',
        'tests/resources/test2.include.txt',
    ] == actual

def test_parse_absolute_path_glob():
    actual = parse_include_paths(f'{root_dir}/**/*.include.txt')
    assert [
        f'{root_dir}/tests/resources/test1.include.txt',
        f'{root_dir}/tests/resources/test2.include.txt',
    ] == actual

@patch.dict(os.environ, {"AI_API_KEY": "env.secret"})
def test_load_api_key_precedence():
    assert "file.secret" == ai_provider_utils.load_api_key(
        "AI_API_KEY",
        token_file_path="tests/resources/example.token",
        token_load_fn="g:LoadToken()",
    )
    assert "fn.secret" == ai_provider_utils.load_api_key(
        "AI_API_KEY",
        token_load_fn="g:LoadToken()",
    )
    assert "env.secret" == ai_provider_utils.load_api_key(
        "AI_API_KEY",
    )

def test_missing_api_key():
    with pytest.raises(KnownError):
        ai_provider_utils.load_api_key("AI_API_KEY_NONEXISTING")

def test_exec_output_is_decoded_text():
    message = make_exec_output_message("printf 'one\\ntwo'")
    assert message == {'type': 'text', 'text': "==> printf 'one\\ntwo' <==\none\ntwo"}

def test_exec_output_reports_timeout():
    message = make_exec_output_message("sleep 2", timeout=0.1)
    assert message['text'] == '==> sleep 2 <==\nCommand timed out after 0.1 seconds'

def test_is_image_path_ignores_case():
    assert is_image_path('photo.PNG')
    assert is_image_path('photo.jpeg')
    assert not is_image_path('notes.txt')

def test_missing_roles_config_function_raises():
    responses = {
        "exists('g:vim_ai_roles_config_function')": '1',
        "g:vim_ai_roles_config_function": 'MissingRoles',
        "exists('*MissingRoles')": '0',
    }
    with patch.object(vim, 'eval', side_effect=responses.get):
        with pytest.raises(Exception, match='Role config function does not exist: MissingRoles'):
            enhance_roles_with_custom_function({})

def test_llm_template_system_and_prompt(tmp_path):
    template = tmp_path / 'both.yaml'
    template.write_text('model: gpt-x\nsystem: be brief\nprompt: summarize\n', encoding='utf-8')
    assert _parse_llm_template_file('both', str(template)) == {
        'both': {
            'options.model': 'gpt-x',
            'options.initial_prompt': '>>> system\n\nbe brief',
            'prompt': 'summarize',
        },
    }

def test_llm_template_prompt_only(tmp_path):
    template = tmp_path / 'prompt.yaml'
    template.write_text('prompt: summarize\n', encoding='utf-8')
    assert _parse_llm_template_file('prompt', str(template)) == {'prompt': {'prompt': 'summarize'}}

def test_markdown_explicit_reasoning_effort_wins_over_model_suffix(tmp_path):
    role = tmp_path / 'effort.md'
    role.write_text('---\nreasoning_effort: low\nmodel: openai:gpt-x-high\n---\nbe brief\n', encoding='utf-8')
    assert _parse_markdown_role_file('effort', str(role))['effort'] == {
        'provider': 'openai',
        'options.model': 'gpt-x',
        'options.reasoning_effort': 'low',
        'options.initial_prompt': '>>> system\n\nbe brief',
    }


def test_print_info_message_keeps_quotes_and_joins_lines():
    from utils import print_info_message
    commands = []
    with patch.object(vim, 'command', side_effect=commands.append):
        print_info_message("it's\nbroken")
    assert "echomsg 'it''s broken'" in commands


def test_image_message_uses_jpeg_mime_type_for_jpg():
    from utils import make_image_message
    message = make_image_message(os.path.join(dirname, 'resources', 'image_file.jpg'))
    assert message['image_url']['url'].startswith('data:image/jpeg;base64,')


def test_model_header_only_splits_registered_provider_prefix():
    from utils import _parse_model_header_value
    assert _parse_model_header_value('openai:gpt-5.2-high') == ('openai', 'gpt-5.2', 'high')
    assert _parse_model_header_value('llama3:8b') == ('', 'llama3:8b', '')
    assert _parse_model_header_value('qwen2.5:7b-instruct') == ('', 'qwen2.5:7b-instruct', '')
