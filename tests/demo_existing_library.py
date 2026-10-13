#!/usr/bin/env python3
"""Reproducible first-cut acceptance; creates only synthetic disposable inputs."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def run(output_parent: Path) -> dict:
    source = Path(__file__).resolve().parents[1]
    run_dir = Path(tempfile.mkdtemp(prefix='first-cut-', dir=output_parent))
    core = run_dir / 'core'
    library = run_dir / 'library'
    for relative in ('scripts/knowledge.py', 'scripts/library.py', 'config/ontology.json'):
        target = core / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source / relative, target)
    (library / 'Lecturas/Adjuntos').mkdir(parents=True)
    (library / 'Borradores').mkdir()
    (library / 'Explicaciones').mkdir()
    (library / 'AGENTS.md').write_text('# Synthetic library rules\nPreserve originals; no migration.\n')
    (library / 'Lecturas/a.md').write_text('---\ntitle: Fictional daytime method\nstatus: imported\n---\n# A\nSynthetic description only.\n![[Adjuntos/method.svg]]\n')
    (library / 'Lecturas/b.md').write_text('# Fictional nighttime method\nSynthetic description only, no real data.\n')
    (library / 'Borradores/comparacion.md').write_text('# Fictional comparison\n[[Lecturas/a]]\n[[Lecturas/b]]\n')
    (library / 'Explicaciones/pregunta.md').write_text('# Synthetic question\nAre the measurement methods comparable?\n')
    (library / 'Lecturas/Adjuntos/method.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg"><text x="0" y="20">Fictional method</text></svg>')
    (library / 'unselected.md').write_text('Synthetic out-of-scope note')
    settings = {'version': 1, 'library_root': 'library',
                'authorized_paths': ['Lecturas', 'Borradores', 'Explicaciones'],
                'objectives': ['Compare fictional measurements'], 'language': 'es',
                'organization': 'preserve', 'initiative': 'within_focus',
                'layers': {'sources': ['Lecturas'], 'drafts': ['Borradores'], 'knowledge': ['Explicaciones']}}
    config = run_dir / 'personal.json'
    config.write_text(json.dumps(settings))
    def snapshot():
        return {p.relative_to(library).as_posix():
                {'sha256': hashlib.sha256(p.read_bytes()).hexdigest(), 'mtime_ns': p.stat().st_mtime_ns}
                for p in library.rglob('*') if p.is_file()}
    before = snapshot()
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')

    def execute(*args, draft=None):
        return subprocess.run([sys.executable, str(core / 'scripts/library.py'), '--config', str(config), *args],
                              input=draft, capture_output=True, text=True, env=env, timeout=10)
    mapped = execute('map', '--scope', 'Lecturas', '--scope', 'Borradores', '--scope', 'Explicaciones')
    assert mapped.returncode == 0, mapped.stderr
    mapping = json.loads(mapped.stdout)
    assert mapping['summary']['notes'] == 4 and mapping['summary']['attachments'] == 1
    assert len(mapping['attachment_links']) == 1
    assert all(p['status'] == 'declared_not_verified' for p in mapping['layer_proposal'])
    selected = execute('read', '--scope', 'Lecturas', '--scope', 'Borradores',
                       '--focus', 'path:Borradores/comparacion.md', '--format', 'markdown')
    assert selected.returncode == 0, selected.stderr
    assert '[[Lecturas/a]]' in selected.stdout and '[[Lecturas/b]]' in selected.stdout
    draft = '# Fictional comparison\nProposed comparison of differing measurement times; no causal equivalence assumed.\n[[Lecturas/a]]\n[[Lecturas/b]]\n'
    proposal = execute('proposal', '--target', 'Borradores/comparacion.md',
                       '--evidence', 'Lecturas/a.md', '--evidence', 'Lecturas/b.md', draft=draft)
    assert proposal.returncode == 0, proposal.stderr
    packet = json.loads(proposal.stdout)
    assert packet['apply_available'] is False and packet['approval_available'] is False
    assert packet['target']['base_sha256'] == before['Borradores/comparacion.md']['sha256']
    assert 'Proposed comparison' in packet['diff']
    denied = execute('map', '--scope', 'unselected.md')
    assert denied.returncode == 2
    assert before == snapshot()
    for name, content in [('map.json', mapped.stdout), ('navigation.md', selected.stdout),
                          ('proposal.json', proposal.stdout)]:
        (run_dir / name).write_text(content)
    receipt = {'status': 'first_cut_tool_acceptance_passed', 'library_unchanged': True,
               'summary': mapping['summary'], 'attachment_content_read': False,
               'out_of_scope_denied': True, 'migration_performed': False, 'proposal_applied': False,
               'private_engine_present': False, 'independent_agent_test': 'not_run',
               'before': before, 'after': snapshot()}
    (run_dir / 'verification.json').write_text(json.dumps(receipt, indent=2))
    return {'artifacts': str(run_dir), **{k: v for k, v in receipt.items() if k not in ('before', 'after')}}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-parent', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.output_parent), indent=2))
