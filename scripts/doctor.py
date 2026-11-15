#!/usr/bin/env python3
"""Read-only entry check for any agent: does this library follow Core, is this the install it names, may the helpers write."""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
import library

CORE = Path(__file__).resolve().parents[1]
SECTION = '## LLM Wiki Core'
FIELDS = {'Core': 'repository', 'Core commit': 'commit', 'Library id': 'library_id'}
UNPINNED = 'unpinned'
LIBRARY_ID = re.compile(r'[a-z0-9][a-z0-9-]{0,63}')
BRIDGES = {'CLAUDE.md': ('@AGENTS.md', '@./AGENTS.md'), 'GEMINI.md': ('@./AGENTS.md', '@AGENTS.md')}
ENV_CORE, ENV_SETTINGS = 'LLM_WIKI_CORE', 'LLM_WIKI_SETTINGS'
LIMIT = 262144


def declaration(text: str) -> dict:
    """Parse the Core section of library rules: three `- Key: value` lines, outside code fences."""
    lines, inside, fenced, found, problems = text.splitlines(), False, False, {}, []
    sections = 0
    for line in lines:
        if re.match(r'\s*(`{3,}|~{3,})', line):
            fenced = not fenced
            continue
        if fenced:
            continue
        if re.match(r'#{1,2} ', line):
            inside = line.strip() == SECTION
            sections += inside
            continue
        match = re.fullmatch(r'- (Core|Core commit|Library id):[ \t]*(.*?)[ \t]*', line) if inside else None
        if match:
            name = FIELDS[match[1]]
            if name in found:
                problems.append(f'"{match[1]}" is declared more than once')
            found.setdefault(name, match[2])
    if sections > 1:
        problems.append(f'"{SECTION}" appears more than once')
    result = {'declared': sections > 0, 'repository': None, 'commit': None, 'pinned': False, 'library_id': None}
    if not sections:
        return {**result, 'problems': problems}
    repository = found.get('repository', '')
    if re.fullmatch(r'https://[A-Za-z0-9.-]+(/[A-Za-z0-9._~-]+)+', repository):
        result['repository'] = repository
    else:
        problems.append('"Core" must be one https address without query, credentials or spaces')
    commit = found.get('commit', '')
    if re.fullmatch(r'[0-9a-f]{40}', commit):
        result.update(commit=commit, pinned=True)
    elif commit != UNPINNED:
        problems.append(f'"Core commit" must be a full 40-character commit or "{UNPINNED}"')
    identifier = found.get('library_id', '')
    if LIBRARY_ID.fullmatch(identifier):
        result['library_id'] = identifier
    else:
        problems.append('"Library id" must be 1 to 64 lowercase letters, digits or hyphens')
    return {**result, 'problems': problems}


def user_config_dir(env) -> Path:
    """The per-user folder that holds one private pointer file per library id; never inside a library."""
    base = env.get('XDG_CONFIG_HOME', '')
    return (Path(base) if base and Path(base).is_absolute() else Path(env.get('HOME') or Path.home()) / '.config') \
        / 'llm-wiki-core'


def read_pointer(path: Path) -> dict:
    """{"version": 1, "core": "/abs", "settings": "/abs"}: private, absolute, nothing else."""
    if path.is_symlink() or not path.is_file():
        raise ValueError('must be a regular file, not a link')
    raw = path.read_bytes()[:65537]
    if len(raw) > 65536:
        raise ValueError('exceeds byte limit')
    data = json.loads(raw)
    if not isinstance(data, dict) or set(data) - {'version', 'core', 'settings'} or data.get('version') != 1:
        raise ValueError('expected {"version": 1, "core": ..., "settings": ...} and nothing else')
    for key in ('core', 'settings'):
        if key in data and (not isinstance(data[key], str) or not Path(data[key]).is_absolute()):
            raise ValueError(f'"{key}" must be an absolute path')
    return data


def same(first, second) -> bool:
    try:
        return os.path.samefile(first, second)
    except OSError:
        return False


def inside(path: Path, boundary: Path | None) -> bool:
    """True when path is the boundary or under it, by resolved spelling or filesystem identity."""
    if boundary is None:
        return False
    resolved, limit = Path(os.path.realpath(path)), Path(os.path.realpath(boundary))
    return resolved == limit or resolved.is_relative_to(limit)


def repository_top(root: Path) -> Path | None:
    """Nearest ancestor holding `.git`, found without running git inside the library."""
    return next((p for p in (root, *root.parents) if (p / '.git').exists()), None)


def git_state(core: Path) -> dict:
    """HEAD and cleanliness of the Core checkout; never refreshes its index."""
    env = dict(os.environ, GIT_OPTIONAL_LOCKS='0', LC_ALL='C')

    def git(*args):
        done = subprocess.run(['git', '-C', str(core), '-c', 'core.fsmonitor=false', *args], env=env,
                              capture_output=True, text=True, timeout=30)
        if done.returncode:
            raise OSError(done.stderr.strip() or 'git failed')
        return done.stdout

    try:
        if not same(git('rev-parse', '--show-toplevel').strip(), core):
            raise OSError('not the top of its own git checkout')
        head = git('rev-parse', 'HEAD').strip()
        status = [line for line in git('status', '--porcelain', '--ignored').splitlines() if line]
    except (OSError, subprocess.SubprocessError) as exc:
        return {'commit': None, 'clean': None, 'detail': str(exc)}
    changed = [line[3:] for line in status if not line.startswith('!!')]
    # Ignored files are not history, but an ignored .pyc beside the helpers is still code Python may load.
    stray = [line[3:] for line in status if line.startswith('!!') and line[3:].startswith('scripts/')]
    return {'commit': head, 'clean': not changed and not stray, 'changed': changed[:20], 'stray_code': stray[:20]}


_PIN_CHECKS = {}


def write_guard(root, core: Path = CORE):
    """Refusal message when this library's rules pin a Core commit that the running install does not match."""
    rules = Path(root) / 'AGENTS.md'
    try:
        if rules.is_symlink() or not rules.is_file():
            return None
        text = rules.read_bytes()[:LIMIT].decode('utf-8')
    except (OSError, UnicodeDecodeError):
        return 'The library rules could not be read; writing is refused until doctor.py reports write mode'
    declared = declaration(text)
    if not declared['declared']:
        return None
    if declared['problems']:
        return 'The Core declaration in the library rules is invalid: ' + '; '.join(declared['problems'])
    if not declared['pinned']:
        return None
    key = (str(core), declared['commit'])
    if key not in _PIN_CHECKS:
        state = git_state(core)
        _PIN_CHECKS[key] = (state.get('commit') == declared['commit'] and state.get('clean') is True)
    if not _PIN_CHECKS[key]:
        return ('The library rules pin Core commit ' + declared['commit'] + ', and this install is not that '
                'clean commit; writing is refused. Run doctor.py --library and work proposal-only.')
    return None


def bridge_state(root: Path) -> dict:
    result = {}
    for name, accepted in BRIDGES.items():
        path = root / name
        if path.is_symlink():
            result[name] = 'link'
        elif not path.exists():
            result[name] = 'absent'
        elif not path.is_file() or path.stat().st_size > 4096:
            result[name] = 'other_content'
        else:
            result[name] = ('imports_rules' if path.read_text(encoding='utf-8', errors='replace').strip() in accepted
                            else 'other_content')
    return result


def report(root: Path, config: Path | None = None, env=None, core: Path = CORE) -> dict:
    env = os.environ if env is None else env
    issues = []

    def issue(kind, detail, blocks=True):
        issues.append({'kind': kind, 'blocks_writing': blocks, 'detail': detail})

    root = library.knowledge.library_root(root)
    if not root.is_dir():
        raise ValueError('Library root must be an existing directory')
    top = repository_top(root)
    rules = root / 'AGENTS.md'
    declared = {'declared': False, 'repository': None, 'commit': None, 'pinned': False, 'library_id': None}
    if rules.is_symlink() or not rules.is_file():
        issue('rules_not_found', 'No regular AGENTS.md in the library root: the rules may have another name; '
                                 'read them, and treat the library as not declaring Core')
    elif rules.stat().st_size > LIMIT:
        issue('rules_too_large', 'AGENTS.md exceeds the byte limit')
    else:
        parsed = declaration(rules.read_text(encoding='utf-8', errors='replace'))
        problems = parsed.pop('problems')
        declared = parsed
        if not declared['declared']:
            issue('core_not_declared', f'The rules have no "{SECTION}" section: they decide the writer; '
                                       'unknown means proposal-only')
        for problem in problems:
            issue('declaration_invalid', problem)
        if declared['declared'] and not declared['pinned'] and not any('Core commit' in p for p in problems):
            issue('core_commit_not_pinned', 'The rules name no commit, so any Core version passes this check. '
                  'The owner pins one before sharing the library or keeping it in Git', blocks=False)

    # Lookup order, each value on its own: explicit argument, environment, the owner's per-user pointer file.
    pointer, pointer_path = {}, None
    if declared['library_id']:
        pointer_path = user_config_dir(env) / (declared['library_id'] + '.json')
        if pointer_path.exists() or pointer_path.is_symlink():
            try:
                pointer = read_pointer(pointer_path)
            except (OSError, ValueError) as exc:
                issue('user_config_invalid', f'{pointer_path}: {exc}')
            for boundary, kind in ((root, 'library'), (top, 'repository')):
                if inside(pointer_path, boundary):
                    issue('user_config_inside_' + kind, f'{pointer_path} is inside the {kind}; it holds private '
                          'paths and belongs in the user configuration folder', blocks=kind == 'library')
                    break
    located = ((env.get(ENV_CORE), ENV_CORE) if env.get(ENV_CORE)
               else (pointer.get('core'), 'user_config') if pointer.get('core') else (None, None))
    core_report = {'path': str(core), 'located_by': located[1], 'commit': None, 'clean': None,
                   'matches_declared': None}
    if located[0] is None:
        issue('core_not_registered', f'This install was not found through {ENV_CORE} or the user configuration '
              'file; it was run by path', blocks=False)
    elif not same(located[0], core):
        issue('core_differs_from_located', f'{located[1]} names {located[0]}, but this report runs from {core}: '
                                           'run the doctor of the located install')
    for boundary, kind in ((root, 'library'), (top, 'repository')):
        if inside(core, boundary):
            issue('core_inside_' + kind, f'This Core install is inside the {kind}; tools that travel with the '
                  'content are not the owner\'s install', blocks=kind == 'library')
            break
    state = git_state(core)
    core_report.update(commit=state['commit'], clean=state['clean'])
    pinned = declared['pinned']
    if state['commit'] is None:
        issue('core_commit_unverified', 'This install is not a readable git checkout, so its version cannot be '
              f'checked ({state["detail"]})', blocks=pinned)
    else:
        if pinned:
            core_report['matches_declared'] = state['commit'] == declared['commit']
            if not core_report['matches_declared']:
                issue('core_commit_mismatch', f'The rules name {declared["commit"]}; this install is at '
                                              f'{state["commit"]}')
        if not state['clean']:
            issue('core_modified', 'This install has local changes or stray code: '
                  + ', '.join([*state['changed'], *state['stray_code']]), blocks=pinned)

    chosen = ((str(config), 'argument') if config is not None
              else (env.get(ENV_SETTINGS), ENV_SETTINGS) if env.get(ENV_SETTINGS)
              else (pointer.get('settings'), 'user_config') if pointer.get('settings') else (None, None))
    settings_report = {'path': chosen[0], 'located_by': chosen[1], 'valid': False, 'same_library': None,
                       'write_policy': None, 'recovery': None}
    if chosen[0] is None:
        where = f', or {pointer_path}' if pointer_path else ''
        issue('settings_not_found', f'No private settings: none in --config, {ENV_SETTINGS}{where}')
    else:
        path = Path(chosen[0])
        try:
            settings = library.load_config(path)
        except (OSError, ValueError, TypeError, RecursionError) as exc:
            issue('settings_invalid', str(exc))
        else:
            policy = settings.get('write_policy', 'read_only')
            settings_report.update(valid=True, write_policy=policy,
                                   same_library=same(settings['library_root'], root))
            if not settings_report['same_library']:
                issue('settings_for_another_library', 'These settings declare a different library_root; two '
                      'libraries may share a Library id, or the wrong file was named')
            if policy == 'read_only':
                issue('write_policy_read_only', 'The settings permit reading only')
            elif policy == 'canonical_engine':
                issue('managed_library', 'A managed engine owns this library: only its own writer saves')
            recovery = settings.get('recovery_directory')
            settings_report['recovery'] = 'outside_library' if recovery else 'not_declared'
            if recovery and inside(Path(recovery), top):
                settings_report['recovery'] = 'inside_repository'
                issue('recovery_inside_repository', 'The recovery directory is inside the Git repository that '
                                                    'holds the library; recovery copies would be published with it')
            for boundary, kind in ((root, 'library'), (top, 'repository')):
                if inside(path, boundary):
                    issue('settings_inside_' + kind, f'The private settings are inside the {kind}; keep them '
                                                     'outside what is shared')
                    break

    bridges = bridge_state(root)
    for name, state_name in bridges.items():
        if state_name in ('other_content', 'link'):
            issue('bridge_not_an_import', f'{name} does not consist of the single import of AGENTS.md; a host '
                  'that reads it may skip or contradict the library rules', blocks=False)
    blocking = [item['kind'] for item in issues if item['blocks_writing']]
    return {
        'library': {'root': str(root), 'rules': 'AGENTS.md' if rules.is_file() and not rules.is_symlink() else None,
                    'git_repository': str(top) if top else None, **declared},
        'core': core_report, 'settings': settings_report, 'bridges': bridges,
        'mode': 'proposal_only' if blocking else 'write',
        'blocked_by': blocking, 'issues': issues,
        'consent': 'not_granted: every write still needs the decision the library rules require',
        'private': 'This report names private paths; keep it out of the library, commits and shared messages.',
        'library_changed': False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--library', type=Path, default=Path('.'), help='library root (default: current folder)')
    parser.add_argument('--config', type=Path, help='private settings; otherwise %s or the user configuration '
                                                    'file named by the Library id' % ENV_SETTINGS)
    args = parser.parse_args()
    try:
        print(json.dumps(report(args.library, args.config), ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, TypeError) as exc:
        print(json.dumps({'error': str(exc)}), file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
