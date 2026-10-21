"""Host-side checks for the no-skills option; no Docker daemon required."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SKILLS_TARGET = 'type=tmpfs,target=/home/dev/.config/opencode/skills'


class NoSkillsSeedTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.home = self.base / 'home'
        self.home.mkdir()
        self.seed = self.base / 'seed'
        (self.seed / 'skills' / 'demo').mkdir(parents=True)
        (self.seed / 'opencode.json').write_text('{"seed": true}')
        (self.seed / 'plugin.txt').write_text('plugin fixture')
        (self.seed / 'skills' / 'demo' / 'SKILL.md').write_text('skill fixture')
        self.cfg = self.home / '.config' / 'opencode'
        self.env = os.environ.copy()
        for name in ('OPENROUTER_API_KEY', 'CLEANROOM_ENV_FILE', 'CLEANROOM_NO_SKILLS'):
            self.env.pop(name, None)
        self.env['HOME'] = str(self.home)
        self.env['CLEANROOM_SEED_DIR'] = str(self.seed)

    def entrypoint(self, no_skills=False):
        env = dict(self.env)
        if no_skills:
            env['CLEANROOM_NO_SKILLS'] = '1'
        result = subprocess.run(['sh', str(ROOT / 'scripts/entrypoint.sh'), 'true'],
                                env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result

    def test_default_seed_includes_skills(self):
        self.entrypoint()
        self.assertEqual((self.cfg / 'opencode.json').read_text(), '{"seed": true}')
        self.assertEqual((self.cfg / 'skills' / 'demo' / 'SKILL.md').read_text(),
                         'skill fixture')

    def test_no_skills_seed_skips_skills_only(self):
        self.entrypoint(no_skills=True)
        self.assertEqual((self.cfg / 'opencode.json').read_text(), '{"seed": true}')
        self.assertEqual((self.cfg / 'plugin.txt').read_text(), 'plugin fixture')
        self.assertFalse((self.cfg / 'skills').exists())

    def test_no_skills_seed_does_not_overwrite_existing_config(self):
        self.cfg.mkdir(parents=True)
        (self.cfg / 'opencode.json').write_text('{"mine": true}')
        self.entrypoint(no_skills=True)
        self.assertEqual((self.cfg / 'opencode.json').read_text(), '{"mine": true}')
        self.assertFalse((self.cfg / 'skills').exists())


class NoSkillsLauncherTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.context = self.base / 'context'
        self.context.mkdir()
        self.env = os.environ.copy()
        for name in ('OPENROUTER_API_KEY', 'CLEANROOM_ENV_FILE', 'CLEANROOM_NO_SKILLS'):
            self.env.pop(name, None)
        self.env['HOME'] = str(self.base / 'home')
        self.env['XDG_DATA_HOME'] = str(self.base / 'storage/data')
        self.env['XDG_CACHE_HOME'] = str(self.base / 'storage/cache')

    def cli(self, *args):
        mock = self.base / 'bin'
        mock.mkdir(exist_ok=True)
        docker = mock / 'docker'
        docker.write_text('#!/usr/bin/env python3\nimport json, os, sys\n'
                          'if sys.argv[1] == "volume": sys.exit(1)\n'
                          'if sys.argv[1] == "run":\n'
                          ' print(json.dumps({"args":sys.argv[1:], "inherited":bool(os.getenv("OPENROUTER_API_KEY"))}))\n')
        docker.chmod(0o755)
        self.env['PATH'] = str(mock) + os.pathsep + os.environ['PATH']
        result = subprocess.run([str(ROOT / 'bin/cleanroom'), *args], cwd=self.context,
                                env=self.env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)['args']

    def test_default_launch_loads_skills(self):
        args = self.cli('--name', 'plain')
        self.assertFalse(any(SKILLS_TARGET in a for a in args))
        self.assertNotIn('CLEANROOM_NO_SKILLS=1', args)

    def test_no_skills_flag_hides_skills_and_marks_entrypoint(self):
        args = self.cli('--name', 'bare', '--no-skills')
        self.assertIn(SKILLS_TARGET, args)
        self.assertIn('CLEANROOM_NO_SKILLS=1', args)
        self.assertIn('type=volume,source=cleanroom-cli-opencode-config,'
                      'target=/home/dev/.config/opencode', args)

    def test_no_skills_env_var_matches_flag(self):
        self.env['CLEANROOM_NO_SKILLS'] = '1'
        args = self.cli('--name', 'bare')
        self.assertIn(SKILLS_TARGET, args)
        self.assertIn('CLEANROOM_NO_SKILLS=1', args)


if __name__ == '__main__':
    unittest.main()
