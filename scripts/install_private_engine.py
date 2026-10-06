#!/usr/bin/env python3
"""Install a pinned, authorized local engine into this same core project.

No download, Git operation, source execution, vault migration or data upload.
Existing differing files are never overwritten. A dependency install is not
production bootstrap, semantic synthesis or authenticated chat approval.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import os
import tempfile

ROOT = Path(__file__).resolve().parents[1]
PIN = ROOT/'config/private-engine-files.json'
SETTINGS = '''---
settings_version: "1.0.0"
promotion_mode: review-first
review_surface: obsidian
automation_preference: manual
git_checkpoints: disabled
memory_mode: off
external_model_processing: forbid
---

# Local settings

One core folder contains the engine and Wiki. These private settings are not
published. Git checkpoints and external model processing remain disabled until
chosen explicitly. Chat approvals are not authenticated by this installer.
'''

def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def child(root: Path, relative: str) -> Path:
    path = PurePosixPath(relative)
    if path.is_absolute() or '..' in path.parts or not path.parts:
        raise ValueError(f'Unsafe manifest path: {relative}')
    result = root.joinpath(*path.parts)
    cursor = result
    while cursor != root:
        if cursor.is_symlink():
            raise ValueError(f'Symlink install paths are unsupported: {relative}')
        if cursor != result and cursor.exists() and not cursor.is_dir():
            raise ValueError(f'Install parent is not a directory: {relative}')
        cursor = cursor.parent
    if root not in result.resolve().parents:
        raise ValueError(f'Install path escapes root: {relative}')
    return result

def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,temporary = tempfile.mkstemp(prefix='.'+path.name+'.',dir=path.parent)
    try:
        with os.fdopen(fd,'wb') as out:
            out.write(data)
            out.flush()
            os.fsync(out.fileno())
        # Install only: an atomic no-clobber link cannot replace a concurrently
        # created destination. The temporary file is in the same filesystem.
        os.link(temporary,path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)

def install(source: Path, target: Path, *, check_only: bool=False) -> dict:
    source=source.resolve(strict=True)
    target=target.resolve(strict=True)
    if not source.is_dir() or not target.is_dir():
        raise ValueError('Source and core root must be existing directories.')
    if source==target:
        raise ValueError('Use the authorized source folder to install into the core folder.')
    pin=json.loads(PIN.read_text())
    material=[]
    for entry in pin['files']:
        src=child(source,entry['path'])
        data=src.read_bytes()
        blob=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
        if sha256(data)!=entry['sha256'] or blob!=entry['git_blob_sha1']:
            raise ValueError('Source hash mismatch: '+entry['path'])
        material.append((entry['path'],data))
    # This generated record contains provenance hashes, not imported vault state.
    material.append(('SOURCE_MANIFEST.json',(json.dumps(pin,indent=2)+'\n').encode()))
    conflicts=[]
    missing=[]
    for relative,data in material:
        dst=child(target,relative)
        if dst.exists():
            if not dst.is_file() or dst.read_bytes()!=data:
                conflicts.append(relative)
        else:
            missing.append((relative,data))
    marker=child(target,'.private-engine-install.json')
    if marker.exists():
        previous=json.loads(marker.read_text())
        if previous.get('source_revision')!=pin['source_revision']:
            conflicts.append('.private-engine-install.json (different installed revision)')
    settings=child(target,'LLM Wiki Settings.md')
    if settings.exists() and not settings.is_file():
        conflicts.append('LLM Wiki Settings.md (not a regular file)')
    for directory in ('Raw','Review','Wiki'):
        required=child(target,directory)
        if required.exists() and not required.is_dir():
            conflicts.append(directory+' (not a directory)')
    # Validate before writing anything. Matching interrupted installs can be rerun.
    if conflicts:
        raise ValueError('Preserved existing differing files; reconcile before install: '+', '.join(conflicts))
    report={'engine_version':pin['engine_version'],'source_revision':pin['source_revision'],
        'root':str(target),'mode':'check' if check_only else 'installed',
        'verified_files':len(pin['files']),'files_to_copy':len(missing),
        'existing_settings':'preserved' if settings.exists() else 'create review-first local defaults',
        'scope':'local engine install only; no authenticated approval host or complete upstream bootstrap'}
    if check_only:
        return report
    for relative,data in missing:
        # Recheck to avoid silently replacing a file created after the preview.
        dst=child(target,relative)
        if dst.exists():
            if dst.read_bytes()!=data:
                raise ValueError('File changed during install; preserved: '+relative)
            continue
        atomic_write(dst,data)
    for directory in ('Raw','Review','Wiki'):
        child(target,directory).mkdir(exist_ok=True)
    if not settings.exists():
        atomic_write(settings,SETTINGS.encode())
    if not marker.exists():
        atomic_write(marker,(json.dumps(report,indent=2)+'\n').encode())
    report['files_copied']=len(missing)
    return report

def main() -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True,help='authorized, locally materialized pinned engine')
    p.add_argument('--root',type=Path,default=ROOT,help='existing core folder (default: this project)')
    p.add_argument('--check',action='store_true',help='verify source and conflicts without writing')
    args=p.parse_args()
    try:
        result=install(args.source,args.root,check_only=args.check)
    except (OSError,ValueError,KeyError) as exc:
        print(json.dumps({'error':str(exc)}))
        return 2
    print(json.dumps(result,indent=2))
    return 0

if __name__=='__main__':
    raise SystemExit(main())
