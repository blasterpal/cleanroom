"""Verify CLI bind mounts and legacy import with Docker; no paid model calls."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import uuid

ROOT = Path(__file__).resolve().parents[1]
IMAGE = os.environ.get('CLEANROOM_IMAGE', 'cleanroom:local')


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='cleanroom-storage-')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.context = self.base / 'context'
        self.context.mkdir()
        (self.context / 'input.txt').write_text('chosen context')
        (self.context / '.env').write_text('OPENROUTER_API_KEY=fixture-storage-key\n')
        (self.context / '.env').chmod(0o600)
        self.env = os.environ.copy()
        self.env.pop('OPENROUTER_API_KEY', None)
        self.env.pop('CLEANROOM_ENV_FILE', None)
        self.env['XDG_DATA_HOME'] = str(self.base / 'share')
        self.env['XDG_CACHE_HOME'] = str(self.base / 'cache')
        self.name = 'verify_' + uuid.uuid4().hex[:12]

    def cli(self, name, commands, extra_args=()):
        result = subprocess.run([str(ROOT / 'bin/cleanroom'), '--name', name, *extra_args],
                                cwd=self.context, env=self.env,
                                input='set -eu\n' + commands + '\n', text=True,
                                capture_output=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr.replace('fixture-storage-key', '<REDACTED>'))
        self.assertNotIn('fixture-storage-key', result.stdout + result.stderr)
        return result

    def test_work_context_auth_and_restart(self):
        self.cli(self.name, """
test "$(pwd)" = /workspace
test "$(cat /context/input.txt)" = 'chosen context'
test ! -s /context/.env
if printf forbidden > /context/input.txt 2>/dev/null; then exit 1; fi
printf work > /workspace/work.txt
printf output > /data/result.txt
printf cached > "$XDG_CACHE_HOME/marker"
printf history > "$XDG_STATE_HOME/marker"
python3 - <<'CHECK'
import json, os, stat
from pathlib import Path
p = Path(os.environ['XDG_DATA_HOME']) / 'opencode/auth.json'
assert json.loads(p.read_text())['openrouter'] == {'type': 'api', 'key': os.environ['OPENROUTER_API_KEY']}
assert stat.S_IMODE(p.stat().st_mode) == 0o600
CHECK
""")
        session = self.base / 'share/cleanroom' / self.name
        self.assertEqual((session / 'workspace/work.txt').read_text(), 'work')
        self.assertEqual((session / 'data/result.txt').read_text(), 'output')
        self.assertEqual((self.context / 'input.txt').read_text(), 'chosen context')
        (session / 'data/extra-context.txt').write_text('injected')
        self.cli(self.name, """
test "$(cat /workspace/work.txt)" = work
test "$(cat /data/result.txt)" = output
test "$(cat /data/extra-context.txt)" = injected
test "$(cat "$XDG_CACHE_HOME/marker")" = cached
test "$(cat "$XDG_STATE_HOME/marker")" = history
""")
        self.cli(self.name + '_other', """
test ! -e /workspace/work.txt
test ! -e /data/result.txt
test ! -e /data/extra-context.txt
test ! -e "$XDG_CACHE_HOME/marker"
test ! -e "$XDG_STATE_HOME/marker"
""")

    def test_no_skills_hides_shared_skills_for_one_launch(self):
        self.cli(self.name, """
test -n "$(ls -A /home/dev/.config/opencode/skills)"
""")
        self.cli(self.name, """
test -z "$(ls -A /home/dev/.config/opencode/skills)"
opencode debug skill | python3 -c "import json, sys; assert json.load(sys.stdin) == []"
""", extra_args=('--no-skills',))
        self.cli(self.name, """
test -n "$(ls -A /home/dev/.config/opencode/skills)"
""")

    def test_legacy_volumes_are_imported_once_and_retained(self):
        volumes = [f'cleanroom-cli-seat-{self.name}-{suffix}'
                   for suffix in ('opencode-data', 'opencode-state', 'cache')]
        try:
            for volume in volumes:
                result = subprocess.run(['docker', 'run', '--rm', '--user', '0',
                                         '--entrypoint', 'sh', '--mount',
                                         f'type=volume,source={volume},target=/legacy',
                                         IMAGE, '-c', 'printf original > /legacy/marker; chown -R 1000:1000 /legacy'],
                                        capture_output=True, timeout=30)
                self.assertEqual(result.returncode, 0)
            self.cli(self.name, """
test "$(cat "$XDG_DATA_HOME/marker")" = original
test "$(cat "$XDG_STATE_HOME/marker")" = original
test "$(cat "$XDG_CACHE_HOME/marker")" = original
printf newer > "$XDG_DATA_HOME/marker"
""")
            self.cli(self.name, 'test "$(cat "$XDG_DATA_HOME/marker")" = newer')
            for volume in volumes:
                result = subprocess.run(['docker', 'run', '--rm', '--entrypoint', 'sh',
                                         '--mount', f'type=volume,source={volume},target=/legacy,readonly',
                                         IMAGE, '-c', 'test "$(cat /legacy/marker)" = original'],
                                        capture_output=True, timeout=30)
                self.assertEqual(result.returncode, 0)
        finally:
            for volume in volumes:
                subprocess.run(['docker', 'volume', 'rm', volume], capture_output=True)


if __name__ == '__main__':
    unittest.main()
