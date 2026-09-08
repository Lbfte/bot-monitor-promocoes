import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import pytest
from monitor.inbox import _responder, AJUDA


class MockState:
    def __init__(self, last_post_id=12345):
        self.last_post_id = last_post_id


class MockSubs:
    def __init__(self, items=None):
        self.items = items or []

    def list_for(self, chat_id):
        return self.items


class TestInboxStatus:
    def test_status_command(self):
        state = MockState(last_post_id=9876)
        subs = MockSubs([{"palavra": "notebook"}, {"palavra": "tv"}])
        res = _responder("/status", 1234, subs, state)
        assert "9876" in res
        assert "2" in res

    def test_ajuda_contains_status(self):
        assert "/status" in AJUDA
