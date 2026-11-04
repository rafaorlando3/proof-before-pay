import json
from pathlib import Path
from unittest.mock import Mock, patch
import unittest

from live_budget import PHASE
import live_entry
import test_live_budget as budget_tests


class LiveEntryTests(unittest.TestCase):
    setUp = budget_tests.LiveBudgetTests.setUp
    save = budget_tests.LiveBudgetTests.save
    read = budget_tests.LiveBudgetTests.read

    def load(self):
        config = self.root / "live.json"
        config.write_text(json.dumps({"enabled": True, "budget_directory": str(self.root),
                          "queue_directory": str(self.root / "queue"), "native_attempt_directory": str(self.root / "attempts"),
                          "fixtures_directory": str(Path(__file__).resolve().parents[1] / "fixtures/cases"),
                          "native_source_revision": "a" * 40, "native_relay": "http://127.0.0.1:18878"}))
        config.chmod(0o600)
        relay = Mock()
        relay.ready.side_effect = OSError("native route down")
        with patch.object(live_entry, "NativeRelay", return_value=relay):
            return live_entry.load_live(config), relay

    def test_exhausted_or_expired_phase_starts_in_recorded_fallback_without_native_request(self):
        self.state[PHASE]["enabled"] = False
        self.save(self.state)
        before = self.path.read_bytes()
        service, relay = self.load()
        status = service.status()
        self.assertEqual(status["mode"], "recorded")
        self.assertFalse(status["available"])
        relay.ready.assert_not_called()
        relay.submit.assert_not_called()
        self.assertEqual(before, self.path.read_bytes())

    def test_unavailable_native_route_does_not_prevent_recorded_viewer_start(self):
        self.state[PHASE]["active_case"] = None
        self.state[PHASE]["expires_at"] = 9999999999
        self.save(self.state)
        service, relay = self.load()
        status = service.status()
        self.assertEqual(status["mode"], "recorded")
        self.assertFalse(status["available"])
        relay.ready.assert_called_once()
        relay.submit.assert_not_called()
