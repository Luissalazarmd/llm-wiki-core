"""Installer regression tests using synthetic directories only."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

BASE=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('private_engine_installer',BASE/'scripts/install_private_engine.py')
installer=importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)
SOURCE=Path(os.environ['LIBRARIAN_ENGINE_SOURCE']).resolve()

class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='synthetic-installer-')
        self.target=Path(self.temp.name)/'core';self.target.mkdir()
    def tearDown(self):
        self.temp.cleanup()
    def snapshot(self):
        return {str(p.relative_to(self.target)):(hashlib.sha256(p.read_bytes()).hexdigest(),p.stat().st_mtime_ns)
                for p in self.target.rglob('*') if p.is_file()}
    def test_check_is_readonly(self):
        r=installer.install(SOURCE,self.target,check_only=True)
        self.assertEqual(r['verified_files'],90)
        self.assertEqual(list(self.target.iterdir()),[])
    def test_reinstall_is_idempotent(self):
        installer.install(SOURCE,self.target)
        before=self.snapshot()
        r=installer.install(SOURCE,self.target)
        self.assertEqual(r['files_copied'],0)
        self.assertEqual(self.snapshot(),before)
    def test_conflict_preserved_before_writes(self):
        (self.target/'LICENSE').write_text('existing different license')
        before=self.snapshot()
        with self.assertRaisesRegex(ValueError,'Preserved existing differing files'):
            installer.install(SOURCE,self.target)
        self.assertEqual(self.snapshot(),before)
    def test_source_corruption_rejected(self):
        source=Path(self.temp.name)/'source';source.mkdir()
        for entry in json.loads(installer.PIN.read_text())['files']:
            dest=source/entry['path'];dest.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(SOURCE/entry['path'],dest)
        (source/'LICENSE').write_text('tampered synthetic source')
        with self.assertRaisesRegex(ValueError,'Source hash mismatch'):
            installer.install(source,self.target)
        self.assertEqual(list(self.target.iterdir()),[])
    def test_symlink_destination_rejected(self):
        outside=Path(self.temp.name)/'outside';outside.mkdir()
        (self.target/'scripts').symlink_to(outside,target_is_directory=True)
        with self.assertRaisesRegex(ValueError,'Symlink'):
            installer.install(SOURCE,self.target)
        self.assertEqual(list(outside.iterdir()),[])
    def test_private_settings_preserved(self):
        settings=self.target/'LLM Wiki Settings.md';settings.write_text('synthetic existing settings')
        installer.install(SOURCE,self.target)
        self.assertEqual(settings.read_text(),'synthetic existing settings')
    def test_required_directory_conflict_precedes_writes(self):
        (self.target/'Raw').write_text('synthetic existing file')
        before=self.snapshot()
        for check in (True,False):
            with self.assertRaisesRegex(ValueError,'Raw .*not a directory'):
                installer.install(SOURCE,self.target,check_only=check)
            self.assertEqual(self.snapshot(),before)
    def test_parent_file_conflict_precedes_writes(self):
        (self.target/'scripts').write_text('synthetic existing file')
        before=self.snapshot()
        with self.assertRaisesRegex(ValueError,'parent is not a directory'):
            installer.install(SOURCE,self.target)
        self.assertEqual(self.snapshot(),before)
    def test_git_policy_keeps_one_repo(self):
        # Local disposable Git only: no remote, credentials, commit or upload.
        shutil.copy2(BASE/'.gitignore',self.target/'.gitignore')
        subprocess.run(['git','init','-q',str(self.target)],check=True)
        manifest=json.loads(installer.PIN.read_text())
        for item in manifest['files']:
            r=subprocess.run(['git','check-ignore','--no-index',item['path']],cwd=self.target,capture_output=True)
            self.assertEqual(r.returncode,0,item['path'])
        for path in ('scripts/install_private_engine.py','adapters/review_chat.py','Raw/source.md',
                     'Review/proposal.md','Wiki/Concepts/note.md'):
            r=subprocess.run(['git','check-ignore','--no-index',path],cwd=self.target,capture_output=True)
            self.assertEqual(r.returncode,1,path)

if __name__=='__main__':
    unittest.main()
