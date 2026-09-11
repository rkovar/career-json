#!/usr/bin/env python3
"""Install real component archives into empty fictional workspaces and test them."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
import build_release
from check_components import check


def extract(archive, root):
    with zipfile.ZipFile(archive) as handle:
        handle.extractall(root)
        for entry in handle.infolist():
            (root / entry.filename).chmod((entry.external_attr >> 16) & 0o777)


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='career-release-')
        self.root=Path(self.tmp.name)
        self.core=build_release.build('core',self.root/'archives')
        self.resume=build_release.build('resume',self.root/'archives')

    def tearDown(self):
        self.tmp.cleanup()

    def command(self, workspace, *args):
        result=subprocess.run(args,cwd=workspace,env={**os.environ,'CAREER_WORKSPACE':str(workspace)},
                              capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        return result

    def test_core_archive_runs_without_resume_code(self):
        workspace=self.root/'core';extract(self.core,workspace)
        self.assertFalse((workspace/'scripts/editorial.py').exists())
        self.assertFalse((workspace/'scripts/select_evidence.py').exists())
        self.assertFalse((workspace/'.claude/skills/make-resume').exists())
        self.command(workspace,'make','check')
        self.command(workspace,sys.executable,'scripts/career_core.py','status')
        self.assertEqual(len(list((workspace/'.claude/skills').glob('*/SKILL.md'))),5)

    def test_addon_installs_without_replacing_core_and_passes_editorial_tests(self):
        workspace=self.root/'combined';extract(self.core,workspace)
        before={str(p.relative_to(workspace)):hashlib.sha256(p.read_bytes()).hexdigest() for p in workspace.rglob('*') if p.is_file()}
        extract(self.resume,workspace)
        for name,digest in before.items():
            self.assertEqual(hashlib.sha256((workspace/name).read_bytes()).hexdigest(),digest,name)
        self.command(workspace,sys.executable,'scripts/check_components.py','--require','resume')
        self.command(workspace,'make','-f','Makefile.resume','check')

    def test_archives_are_reproducible_and_exclude_private_paths(self):
        for component,archive in [('core',self.core),('resume',self.resume)]:
            again=build_release.build(component,self.root/'again')
            self.assertEqual(archive.read_bytes(),again.read_bytes())
            with zipfile.ZipFile(archive) as handle:
                for name in handle.namelist():
                    self.assertNotIn(Path(name).parts[0],build_release.PRIVATE)
                inventory=json.loads(handle.read(f'components/{component}/release.json'))
                for name,digest in inventory['files'].items():
                    self.assertEqual(hashlib.sha256(handle.read(name)).hexdigest(),digest)

    def test_wrong_or_missing_core_version_blocks_addon(self):
        workspace=self.root/'combined';extract(self.resume,workspace)
        with self.assertRaisesRegex(ValueError,'Core is not installed'):
            check(workspace,require='resume')
        extract(self.core,workspace)
        path=workspace/'components/core/component.json'
        record=json.loads(path.read_text());record['version']='99.0.0';path.write_text(json.dumps(record))
        with self.assertRaisesRegex(ValueError,'requires career-core'):
            check(workspace,require='resume')
        # An incompatible add-on does not disable independent core use.
        self.assertEqual(check(workspace,require='core'),'99.0.0')

    def test_core_build_does_not_depend_on_resume_release_health(self):
        original = build_release.entries
        def unavailable_resume(component, root=ROOT):
            if component == 'resume':
                raise ValueError('resume release is temporarily broken')
            return original(component, root)
        with patch.object(build_release, 'entries', side_effect=unavailable_resume):
            self.assertTrue(build_release.build('core', self.root / 'independent').is_file())
            with self.assertRaisesRegex(ValueError, 'temporarily broken'):
                build_release.build('resume', self.root / 'independent')

    def test_private_sources_and_symlinks_cannot_enter_allowlist(self):
        for path in ['data/packs/career.json','reviews/answers.md','outputs/resume.md','../secret','.git/config','/tmp/private']:
            with self.assertRaises(ValueError):build_release.public_path(path)
        staging=self.root/'source';shutil.copytree(ROOT/'components',staging/'components')
        mapping=build_release.manifest('core',staging)
        mapping['files']={'docs/leak.md':'docs/leak.md'}
        (staging/'components/core/component.json').write_text(json.dumps(mapping))
        (staging/'docs').mkdir();(staging/'private.txt').write_text('PRIVATE_CANARY')
        (staging/'docs/leak.md').symlink_to(staging/'private.txt')
        with self.assertRaisesRegex(ValueError,'symlink'):build_release.entries('core',staging)


if __name__ == '__main__':
    unittest.main(verbosity=2)
