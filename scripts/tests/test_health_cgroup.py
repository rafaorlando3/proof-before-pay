"""Health must reject the captured kernel-OOM condition, even with IRIS alive."""
from pathlib import Path
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'check_cgroup_oom.sh'


class CgroupHealthTests(unittest.TestCase):
    def run_check(self, content=None, relative='memory.events', identity='0::/\n', other=None):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            proc = root / 'self-cgroup'
            proc.write_text(identity)
            if other:
                extra = root / other[0]
                extra.parent.mkdir(parents=True, exist_ok=True)
                extra.write_text(other[1])
            if content is not None:
                target = root / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content)
            return subprocess.run(['sh', str(SCRIPT), str(root), str(proc)], capture_output=True, text=True)

    def test_captured_OOM_kills_fail_even_if_supervisor_would_be_healthy(self):
        captured = 'low 0\nhigh 0\nmax 11770\noom 4\noom_kill 3\noom_group_kill 0\n'
        result = self.run_check(captured)
        self.assertEqual(result.returncode, 1)
        self.assertIn('PBP_HEALTH=oom_kill_detected count=3', result.stderr)

    def test_pressure_without_a_kernel_kill_does_not_claim_worker_death(self):
        result = self.run_check('low 0\nhigh 1\nmax 2\noom 1\noom_kill 0\n')
        self.assertEqual(result.returncode, 0)

    def test_v1_counter_is_supported(self):
        result = self.run_check('oom_kill_disable 0\nunder_oom 0\noom_kill 1\n',
                                'memory/memory.oom_control', identity='9:memory:/\n')
        self.assertEqual(result.returncode, 1)
        self.assertIn('oom_kill_detected', result.stderr)

    def test_invalid_or_ambiguous_exposed_counter_fails_closed(self):
        for content in ['oom_kill\n', 'oom_kill invalid\n', 'oom_kill 0\noom_kill 1\n']:
            with self.subTest(content=content):
                result = self.run_check(content)
                self.assertEqual(result.returncode, 1)
                self.assertIn('oom_telemetry_invalid', result.stderr)

    def test_host_namespace_root_OOM_does_not_poison_container_health(self):
        result = self.run_check('oom_kill 99\n', identity='0::/docker/own-id\n')
        self.assertEqual(result.returncode, 0)
        self.assertIn('cgroup_namespace_not_private', result.stderr)

    def test_v1_old_kernel_without_kill_counter_is_unavailable(self):
        result = self.run_check('oom_kill_disable 0\nunder_oom 0\n',
                                'memory/memory.oom_control', identity='9:memory:/\n')
        self.assertEqual(result.returncode, 0)
        self.assertIn('counter_field_missing', result.stderr)

    def test_v1_host_hierarchy_resolves_only_self_counter(self):
        result = self.run_check('oom_kill 0\n', 'memory/docker/own/memory.oom_control',
                                identity='9:memory:/docker/own\n',
                                other=('memory/memory.oom_control', 'oom_kill 99\n'))
        self.assertEqual(result.returncode, 0)
        self.assertNotIn('oom_kill_detected', result.stderr)
        result = self.run_check('oom_kill 2\n', 'memory/docker/own/memory.oom_control',
                                identity='9:memory:/docker/own\n')
        self.assertEqual(result.returncode, 1)
        self.assertIn('count=2', result.stderr)

    def test_unavailable_telemetry_leaves_standard_readiness_checks_in_charge(self):
        self.assertEqual(self.run_check().returncode, 0)


if __name__ == '__main__':
    unittest.main()
