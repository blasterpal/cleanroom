"""Host-side regression checks; no provider credentials or Docker daemon required."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class AuthenticationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.env = os.environ.copy()
        for name in ('OPENROUTER_API_KEY', 'CLEANROOM_ENV_FILE'):
            self.env.pop(name, None)
        self.env['HOME'] = str(self.base / 'home')
        self.env['XDG_DATA_HOME'] = str(self.base / 'data')

    def entrypoint(self, key=None):
        if key is not None:
            self.env['OPENROUTER_API_KEY'] = key
        return subprocess.run(['sh', str(ROOT / 'scripts/entrypoint.sh'), 'true'],
                              env=self.env, capture_output=True, text=True)

    def test_seed_merge_permissions_and_empty_key(self):
        auth = self.base / 'data/opencode/auth.json'
        auth.parent.mkdir(parents=True)
        auth.write_text('{"other":{"type":"api","key":"other-fixture"}}')
        key = 'fixture-"quoted"-\\-key'
        result = self.entrypoint(key)
        self.assertEqual(result.returncode, 0)
        value = json.loads(auth.read_text())
        self.assertEqual(value['openrouter'], {'type': 'api', 'key': key})
        self.assertEqual(value['other']['key'], 'other-fixture')
        self.assertEqual(auth.stat().st_mode & 0o777, 0o600)
        before = auth.read_bytes()
        self.assertEqual(self.entrypoint('').returncode, 0)
        self.assertEqual(auth.read_bytes(), before)
        self.env.pop('OPENROUTER_API_KEY')
        self.assertEqual(self.entrypoint().returncode, 0)
        self.assertEqual(auth.read_bytes(), before)
        self.assertNotIn(key, result.stdout + result.stderr)

    def test_fresh_default_data_home_and_missing_key(self):
        self.env.pop('XDG_DATA_HOME')
        auth = Path(self.env['HOME']) / '.local/share/opencode/auth.json'
        self.assertEqual(self.entrypoint().returncode, 0)
        self.assertFalse(auth.exists())
        self.assertEqual(self.entrypoint('fixture').returncode, 0)
        self.assertEqual(json.loads(auth.read_text())['openrouter']['key'], 'fixture')
        self.assertEqual(auth.stat().st_mode & 0o777, 0o600)

    def test_invalid_auth_is_preserved_without_leaking_content(self):
        auth = self.base / 'data/opencode/auth.json'
        auth.parent.mkdir(parents=True)
        auth.write_text('{"key":"private-fixture", broken')
        result = self.entrypoint('new-fixture')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(auth.read_text(), '{"key":"private-fixture", broken')
        self.assertNotIn('private-fixture', result.stderr + result.stdout)
        self.assertNotIn('new-fixture', result.stderr + result.stdout)

    def cli(self, *args):
        mock = self.base / 'bin'
        mock.mkdir(exist_ok=True)
        docker = mock / 'docker'
        docker.write_text('#!/usr/bin/env python3\nimport json, os, sys\n'
                          'if sys.argv[1] == "run":\n'
                          ' print(json.dumps({"args":sys.argv[1:], "inherited":bool(os.getenv("OPENROUTER_API_KEY"))}))\n')
        docker.chmod(0o755)
        self.env['PATH'] = str(mock) + os.pathsep + os.environ['PATH']
        return subprocess.run([str(ROOT / 'bin/cleanroom'), *args], cwd=self.base,
                              env=self.env, capture_output=True, text=True)

    def test_cwd_env_and_shell_override_without_secret_arguments(self):
        (self.base / '.env').write_text('OPENROUTER_API_KEY=fixture-file-key\n')
        self.env['OPENROUTER_API_KEY'] = 'fixture-shell-key'
        result = self.cli('--name', 'test')
        self.assertEqual(result.returncode, 0)
        args = json.loads(result.stdout)['args']
        self.assertEqual(args[args.index('--env-file') + 1], str(self.base / '.env'))
        self.assertIn('OPENROUTER_API_KEY', args)
        self.assertTrue(any('target=/workspace/.env' in a for a in args))
        self.assertNotIn('fixture-shell-key', result.stdout + result.stderr)
        self.assertNotIn('fixture-file-key', result.stdout + result.stderr)

    def test_file_only_and_no_checkout_env_fallback(self):
        result = self.cli('--name', 'test')
        self.assertEqual(result.returncode, 0)
        self.assertNotIn('--env-file', json.loads(result.stdout)['args'])
        (self.base / '.env').write_text('OPENROUTER_API_KEY=fixture-file-key\n')
        result = self.cli('--name', 'test')
        invocation = json.loads(result.stdout)
        self.assertEqual(invocation['args'][invocation['args'].index('--env-file') + 1],
                         str(self.base / '.env'))
        self.assertNotIn('OPENROUTER_API_KEY', invocation['args'])
        self.assertFalse(invocation['inherited'])

    def test_explicit_env_file_is_preserved_and_hidden(self):
        selected = self.base / 'credentials.env'
        selected.write_text('OPENROUTER_API_KEY=fixture-selected-key\n')
        result = self.cli('--name', 'selected', '--env-file', str(selected))
        self.assertEqual(result.returncode, 0)
        args = json.loads(result.stdout)['args']
        self.assertEqual(args[args.index('--env-file') + 1], str(selected))
        self.assertTrue(any('target=/workspace/credentials.env' in a for a in args))
        self.assertNotEqual(self.cli('--name', 'selected', '--env-file', str(self.base / 'missing')).returncode, 0)

    def test_onepassword_exports_key_without_rewriting_env(self):
        checkout = self.base / 'checkout'
        (checkout / 'scripts').mkdir(parents=True)
        script = checkout / 'scripts/up'
        script.write_bytes((ROOT / 'scripts/up').read_bytes())
        original = 'OPENROUTER_API_KEY=old-fixture-key\nOTHER=kept\n'
        (checkout / '.env').write_text(original)
        mock = self.base / 'bin'
        mock.mkdir()
        (mock / 'op').write_text('#!/bin/sh\nprintf %s fixture-onepassword-key\n')
        (mock / 'docker').write_text(
            '#!/bin/sh\n[ "$OPENROUTER_API_KEY" = fixture-onepassword-key ] || exit 1\n')
        for executable in mock.iterdir():
            executable.chmod(0o755)
        self.env.update(PATH=str(mock) + os.pathsep + os.environ['PATH'],
                        OPENROUTER_OP_REF='op://fixture/item/key',
                        OPENROUTER_KEY_CACHE=str(self.base / 'cache/key'))
        for _ in range(2):
            result = subprocess.run(['sh', str(script)], env=self.env,
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 0)
            self.assertEqual((checkout / '.env').read_text(), original)
            self.assertNotIn('fixture-onepassword-key', result.stdout + result.stderr)

        (mock / 'op').write_text('#!/bin/sh\necho fixture-onepassword-key >&2\nexit 1\n')
        self.env['OPENROUTER_KEY_CACHE_TTL'] = '0'
        failed = subprocess.run(['sh', str(script)], env=self.env,
                                capture_output=True, text=True)
        self.assertNotEqual(failed.returncode, 0)
        self.assertNotIn('fixture-onepassword-key', failed.stdout + failed.stderr)

    def test_named_volumes_are_isolated_and_reused(self):
        results = [self.cli('--name', name) for name in ('a', 'b')]
        for result in results:
            self.assertEqual(result.returncode, 0)
        mounts = [[a for a in json.loads(r.stdout)['args'] if 'type=volume' in a]
                  for r in results]
        for target in ('/home/dev/.local/share', '/home/dev/.local/state', '/home/dev/.cache'):
            self.assertNotEqual(next(m for m in mounts[0] if 'target=' + target in m),
                                next(m for m in mounts[1] if 'target=' + target in m))
        self.assertEqual(next(m for m in mounts[0] if 'target=/home/dev/.config/opencode' in m),
                         next(m for m in mounts[1] if 'target=/home/dev/.config/opencode' in m))
        resumed = self.cli('--name=a')
        self.assertEqual(json.loads(resumed.stdout)['args'], json.loads(results[0].stdout)['args'])
        self.assertIn('source=cleanroom-cli-seat-a-opencode-data,target=', resumed.stdout)

    def test_launch_requires_a_nonempty_name(self):
        for args in ((), ('--name',), ('--name=',), ('--name', ''),
                     ('--name', '!@#$%^&*()./'), ('--seat', 'a')):
            with self.subTest(args=args):
                result = self.cli(*args)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout, '')
        self.assertEqual(self.cli('--help').returncode, 0)
        self.assertEqual(self.cli('build').returncode, 0)
        self.assertEqual(self.cli('install').returncode, 0)

    def test_name_normalization(self):
        for raw, normalized in (('Login fix-v2!', 'Login_fix_v2'),
                                ('a.b/@c', 'abc'), ('a \t-b', 'a___b'),
                                ('../other', 'other'), ('hello_world', 'hello_world')):
            with self.subTest(raw=raw):
                result = self.cli('--name', raw)
                self.assertEqual(result.returncode, 0)
                args = json.loads(result.stdout)['args']
                self.assertIn(f'type=volume,source=cleanroom-cli-seat-{normalized}-opencode-data,target=/home/dev/.local/share', args)
                equivalent = self.cli('--name', normalized)
                self.assertEqual(args, json.loads(equivalent.stdout)['args'])



if __name__ == '__main__':
    unittest.main()
