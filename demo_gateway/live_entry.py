"""Explicit operator entry for the optional live viewer. No implicit activation."""
from pathlib import Path
import json
import sys

# -I removes the script directory from sys.path. Only this fixed, operator-owned
# bundle is added; no module name or import directory comes from an HTTP caller.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_budget import LiveBudget, require
from live_native import FIXTURES, NativeRelay, NativeRunner
from live_queue import LiveQueue
from live_service import LiveService
from server import Config, serve


def load_live(path):
    source = Path(path)
    require(not source.is_symlink() and not source.stat().st_mode & 0o077, "private_live_config_required")
    data = json.loads(source.read_text())
    required = {"enabled", "budget_directory", "queue_directory", "native_attempt_directory",
                "fixtures_directory", "native_source_revision", "native_relay"}
    require(isinstance(data, dict) and set(data) == required and type(data["enabled"]) is bool, "explicit_live_config_required")
    budget = LiveBudget(data["budget_directory"])
    relay = NativeRelay(data["native_relay"], expected_revision=data["native_source_revision"])
    runner = NativeRunner(data["fixtures_directory"], data["native_attempt_directory"], relay)
    queue = LiveQueue(data["queue_directory"], FIXTURES, enabled=data["enabled"])
    # Runtime admission checks every independent gate. An exhausted quota,
    # expired phase, uncertain in-flight job or unavailable native route must
    # leave the recorded viewer usable after a service restart.
    return LiveService(queue, budget, runner, relay.ready, enabled=data["enabled"])


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--viewer-config", required=True)
    parser.add_argument("--live-config", required=True)
    parser.add_argument("--port", type=int, default=18879)
    args = parser.parse_args()
    serve(Config.load(args.viewer_config), port=args.port, live=load_live(args.live_config))
