import json
import pytest
from app.agents.supervisor import live_plan
from app.config import Settings


class FakeResponse:
    def __init__(self, body):
        self.body = body

    def raise_for_status(self):
        return None

    def json(self):
        return self.body


def test_openrouter_chat_completions_tool_call(monkeypatch):
    captured = {}
    args = {'tools': [{'name': 'get_balance', 'resource_id': None, 'period': 'all'}],
            'requires_rag': False, 'missing_information': []}

    def fake_post(url, **kwargs):
        captured.update(url=url, **kwargs)
        return FakeResponse({'choices': [{'message': {'tool_calls': [{
            'function': {'name': 'plan_banking_request', 'arguments': json.dumps(args)}
        }]}}]})

    monkeypatch.setattr('app.agents.supervisor.httpx.post', fake_post)
    settings = Settings(router_mode='openrouter', openrouter_api_key='test-only',
                        openrouter_model='nvidia/nemotron-3.5-lightning:free')
    plan = live_plan('What is my balance?', settings)
    assert captured['url'] == 'https://openrouter.ai/api/v1/chat/completions'
    assert captured['json']['model'] == 'nvidia/nemotron-3.5-lightning:free'
    assert captured['json']['tool_choice']['function']['name'] == 'plan_banking_request'
    assert plan.required_tools[0].name == 'get_balance'
    assert plan.requires_pin is True


def test_openrouter_rejects_unstructured_or_missing_tool_call(monkeypatch):
    monkeypatch.setattr('app.agents.supervisor.httpx.post', lambda *a, **k: FakeResponse({'choices': [{'message': {'content': 'just text'}}]}))
    settings = Settings(router_mode='openrouter', openrouter_api_key='test-only')
    with pytest.raises(ValueError, match='Invalid planner output'):
        live_plan('What is my balance?', settings)
