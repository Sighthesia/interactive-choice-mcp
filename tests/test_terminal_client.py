import sys
import json
import types

import pytest

from src.terminal import client


class DummyResp:
    def __init__(self, status_code=200, data=None):
        self.status_code = status_code
        self._data = data or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"status {self.status_code}")

    def json(self):
        return self._data


def test_submit_result_calls_httpx_post(monkeypatch):
    calls = {}

    def fake_post(url, json=None, timeout=None):
        calls['url'] = url
        calls['json'] = json
        calls['timeout'] = timeout
        class R: pass
        return R()

    monkeypatch.setattr(client, 'httpx', types.SimpleNamespace(post=fake_post))

    client._submit_result('http://127.0.0.1:8000', 's1', ['A'], {'A': 'note'}, 'glob')
    assert calls['url'].endswith('/terminal/s1/submit')
    assert calls['json']['action_status'] == 'selected'
    assert calls['json']['selected_indices'] == ['A']


def test_submit_cancelled_calls_httpx_post(monkeypatch):
    calls = {}

    def fake_post(url, json=None, timeout=None):
        calls['url'] = url
        calls['json'] = json

    monkeypatch.setattr(client, 'httpx', types.SimpleNamespace(post=fake_post))

    client._submit_cancelled('http://127.0.0.1:8000', 's2')
    assert calls['url'].endswith('/terminal/s2/submit')
    assert calls['json']['action_status'] == 'cancelled'


def test_main_returns_1_when_session_not_found(monkeypatch, capsys):
    monkeypatch.setattr(client, 'httpx', types.SimpleNamespace(get=lambda url, timeout=None: DummyResp(status_code=404)))
    monkeypatch.setattr(sys, 'argv', ['prog', '--session', 's3', '--url', 'http://127.0.0.1:8000'])
    rv = client.main()
    assert rv == 1
    captured = capsys.readouterr()
    assert 'Session not found' in captured.err


def test_main_completed_session_prints_result(monkeypatch, capsys):
    data = {'status': 'completed', 'result': {'action_status': 'cancelled', 'summary': 'no selection'}}
    monkeypatch.setattr(client, 'httpx', types.SimpleNamespace(get=lambda url, timeout=None: DummyResp(status_code=200, data=data)))
    monkeypatch.setattr(sys, 'argv', ['prog', '--session', 's4', '--url', 'http://127.0.0.1:8000'])
    rv = client.main()
    assert rv == 0
    captured = capsys.readouterr()
    assert 'Session already completed' in captured.out
    assert 'cancelled' in captured.out
