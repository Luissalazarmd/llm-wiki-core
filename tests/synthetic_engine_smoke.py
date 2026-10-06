#!/usr/bin/env python3
"""Bounded integration fixture, never a host-authenticated approval bridge.
Run only in a fresh network namespace. All approval events below are simulated.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--engine-root', type=Path, required=True)
    p.add_argument('--output-parent', type=Path, required=True)
    p.add_argument('--synthetic-only', action='store_true', required=True)
    args = p.parse_args()
    engine = args.engine_root.resolve(strict=True)
    baseline = Path(__file__).resolve().parents[1]
    output_parent = args.output_parent.resolve()
    if any(output_parent == forbidden or forbidden in output_parent.parents
           for forbidden in (baseline, engine)):
        raise SystemExit('Synthetic outputs must be outside baseline and engine directories.')
    # Require a network namespace different from the invoking host's recorded one.
    host_ns = os.environ.get('LIBRARIAN_HOST_NETNS')
    current_ns = os.readlink('/proc/self/ns/net')
    if not host_ns or host_ns == current_ns:
        raise SystemExit('Run through the documented fresh unshare network namespace.')
    args.output_parent.mkdir(parents=True, exist_ok=True)
    output = Path(tempfile.mkdtemp(prefix='synthetic-', dir=args.output_parent))
    root = output / 'instance'
    root.mkdir()
    evidence = output / 'evidence'
    evidence.mkdir()
    (root/'SYNTHETIC_ONLY.json').write_text(json.dumps({
        'synthetic_only': True, 'user_knowledge': False,
        'approval': 'SIMULATED TEST EVENT, NOT AUTHENTICATED HUMAN APPROVAL'}))
    for directory in ('Raw','Wiki','Review'):
        (root/directory).mkdir()
    shutil.copytree(engine/'Schema', root/'Schema')
    shutil.copytree(engine/'_templates', root/'_templates')
    shutil.copy2(engine/'LICENSE', root/'LICENSE')
    policy_path = root/'Schema/librarian-policy.json'
    policy = json.loads(policy_path.read_text())
    policy['git']['enabled'] = False
    policy['memory']['enabled'] = False
    policy['privacy']['external_model_processing'] = 'forbid'
    policy['mode'] = 'review-first'
    policy_path.write_text(json.dumps(policy, indent=2)+'\n')
    sys.path.insert(0, str(engine/'scripts'))
    from librarian.apply import apply_held_proposal, apply_source_scan
    from librarian.contracts import content_sha256
    from librarian.decisions import StaleDecision, decide_case
    from librarian.proposals import validate_proposal
    from librarian.review import upsert_case, list_cases
    from librarian.runs import RunRecorder, load_receipts, utc_now
    from librarian.sources import scan_source_state, normalized_body
    from librarian.transactions import (InjectedCrash, RecoveryConflict, apply_transaction,
        recover_transaction, file_sha256, incomplete_transactions)
    passed = []
    def check(name, condition, detail=None):
        if not condition:
            raise AssertionError(f'{name}: {detail}')
        passed.append(name)
    def save(name, obj):
        (evidence/name).write_text(json.dumps(obj, ensure_ascii=False, indent=2)+'\n')
    def recorder(goal):
        return RunRecorder.start(root, goal, mode='review-first', trigger='script',
            backend='filesystem', invoker={'agent':'synthetic-test-harness',
            'integration':'synthetic-test', 'model':'none'})
    def snapshot():
        return {str(f.relative_to(root)): [hashlib.sha256(f.read_bytes()).hexdigest(),
            f.stat().st_mtime_ns, f.stat().st_size] for f in root.rglob('*') if f.is_file()}
    source_text = '''---
Title: Synthetic Source
Created: 2026-10-06
---
# Synthetic Source

Material inventado exclusivamente para esta prueba. El concepto sintético tiene una propiedad de prueba.
'''
    source = root/'Raw/synthetic.md'
    source.write_text(source_text)
    scan = scan_source_state(root, update=False)
    check('source_detected', scan['actionable_count']==1 and not scan['errors'], scan)
    scan_receipt, scan_checkpoint = apply_source_scan(root, recorder('Synthetic capture scan'), scan)
    check('source_scan_receipt', scan_checkpoint['phase']=='finalized')
    check('source_scan_no_work', scan_source_state(root, update=False)['actionable_count']==0)
    target = 'Wiki/Concepts/synthetic.md'
    content = '''---
type: Concept
tags:
  - concept
topics: []
status: seed
created: 2026-10-06
updated: 2026-10-06
sources:
  - "[[Raw/synthetic]]"
source_count: 1
origin: ai
generated: []
verified: []
---

# Concepto sintético

## Details

El concepto sintético tiene una propiedad de prueba. Contenido inventado, sin valor como evidencia real.

## Related

Todavía no hay otras páginas compiladas en esta instancia de prueba.

## Sources

- [[Raw/synthetic]]
'''
    held_run = recorder('Synthetic proposal awaiting simulated review')
    payload = {'run_id':held_run.run_id,'created_at':utc_now(),'mode':'review-first',
        'goal':'Create one fabricated Spanish concept for integration testing',
        'base_targets':[], 'changes':[{'operation':'create','path':target,'content':content}],
        'reason_codes':[], 'source_refs':['Raw/synthetic.md'],
        'dependencies':['Raw/synthetic.md'], 'model_provider':'deterministic',
        'page_plan':[], 'evidence_anchors':[{'source_ref':'Raw/synthetic.md',
            'anchor':'El concepto sintético tiene una propiedad de prueba.',
            'source_sha256':content_sha256(normalized_body(source_text))}]}
    validation = validate_proposal(root, payload)
    check('proposal_valid_review_first', validation['valid'] and not validation['issues']
        and not validation['auto_eligible'] and validation['access']['allow'], validation)
    proposal = validation['proposal']
    case = upsert_case(root, case_type='proposal', target=target, reason='REVIEW_REQUIRED',
        evidence_anchor='Raw/synthetic.md', run_id=held_run.run_id,
        reason_codes=['REVIEW_REQUIRED'], evidence=[{'source':'Raw/synthetic.md',
        'anchor':'El concepto sintético tiene una propiedad de prueba.'}],
        proposal_revision=proposal['proposal_id'], payload={'proposal_id':proposal['proposal_id'],
        'validation_reason_codes':validation['reason_codes']}, persist=False)
    case['dependencies'] = proposal['dependencies']
    case['etag'] = content_sha256({k:v for k,v in case.items() if k!='etag'})
    held_receipt, held_checkpoint = apply_held_proposal(root, held_run, case, proposal,
        validation, 'Synthetic proposal held for SIMULATED review')
    check('proposal_held_no_page', held_receipt['verdict']=='held' and not (root/target).exists())
    check('one_review_case', len(list_cases(root))==1)
    save('held-receipt.json',held_receipt)
    adapter = Path(__file__).resolve().parents[1]/'adapters/review_chat.py'
    cmd = [sys.executable, str(adapter),'--engine-root',str(engine),'--instance-root',str(root)]
    before = snapshot()
    outputs = {}
    for op in ('list','show','packet'):
        argv = cmd+[op]+([] if op=='list' else [case['case_id']])
        one = subprocess.run(argv, capture_output=True, text=True, check=True)
        two = subprocess.run(argv, capture_output=True, text=True, check=True)
        check('readonly_'+op, one.stdout==two.stdout and snapshot()==before)
        outputs[op]=json.loads(one.stdout)
        save(op+'.json', outputs[op])
    packet = outputs['packet']
    check('packet_full_proposal',packet['proposal_envelope']==proposal and
        packet['approval_available'] is False and bool(packet['detail']['diffs'][0]['diff']))
    packet_bytes = json.dumps({k:packet[k] for k in ('case','proposal_envelope','detail')},
        sort_keys=True,ensure_ascii=False,separators=(',',':')).encode('utf-8')
    check('packet_hash_matches',hashlib.sha256(packet_bytes).hexdigest()==packet['display_sha256'])
    for bad_case,label in (('../x','malformed'),('case_missing_synthetic','missing')):
        failed = subprocess.run(cmd+['packet',bad_case],capture_output=True,text=True)
        check('readonly_reject_'+label,failed.returncode==2 and not failed.stdout and
              bool(json.loads(failed.stderr)['error']) and snapshot()==before)
    for drift in ('source','target'):
        stale_root = output/('stale-'+drift+'-instance')
        shutil.copytree(root,stale_root)
        stale_target = stale_root/target
        if drift == 'source':
            (stale_root/'Raw/synthetic.md').write_text(source_text+'\nChanged source fixture.\n')
        else:
            stale_target.parent.mkdir(parents=True,exist_ok=True)
            stale_target.write_text('Preserve this synthetic manual edit')
        stale_run = RunRecorder.start(stale_root,'Synthetic stale '+drift,mode='review-first')
        stale_result = decide_case(stale_root,stale_run,case['case_id'],case['case_revision'],
            case['etag'],'approve','synthetic-test-reviewer',memory_preference='skip')
        preserved = (not stale_target.exists() if drift == 'source' else
                     stale_target.read_text()=='Preserve this synthetic manual edit')
        check('canonical_stale_'+drift+'_blocks_apply',
              stale_result['case']['status']=='stale' and preserved, stale_result)
    decision_run = recorder('SIMULATED synthetic reviewer approval')
    for rev,etag,label in ((case['case_revision']+1,case['etag'],'revision'),
                          (case['case_revision'],'incorrect-etag','etag')):
        before = snapshot()
        try:
            decide_case(root,decision_run,case['case_id'],rev,etag,'approve','synthetic-test-reviewer')
        except StaleDecision:
            check('stale_'+label+'_no_mutation',snapshot()==before)
        else:
            raise AssertionError('Stale '+label+' was accepted')
    source.write_text(source_text+'\nSource changed after review packet.\n')
    changed_validation = validate_proposal(root,proposal)
    check('source_drift_detected','SOURCE_DRIFT' in changed_validation['reason_codes'])
    source.write_text(source_text)
    # Simulated manual collision: this is test setup, not a production Wiki edit.
    (root/target).parent.mkdir(parents=True,exist_ok=True)
    (root/target).write_text('Synthetic competing manual note')
    check('target_collision_detected','TARGET_REVISION_CHANGED' in
        validate_proposal(root,proposal)['reason_codes'])
    (root/target).unlink()
    result = decide_case(root,decision_run,case['case_id'],case['case_revision'],case['etag'],
        'approve','synthetic-test-reviewer',rationale='SIMULATED approval of invented test content.',
        memory_preference='skip',client_idempotency_key='synthetic-test-approval-1')
    check('canonical_apply_receipt',result['receipt']['verdict']=='pass' and
        result['checkpoint']['phase']=='finalized' and result['case']['status']=='resolved', result)
    check('spanish_note_created',(root/target).exists() and 'Concepto sintético' in (root/target).read_text())
    check('source_preserved',source.read_text()==source_text)
    save('apply-receipt.json',result['receipt'])
    save('simulated-decision.json',result['decision'])
    before = snapshot()
    try:
        decide_case(root,decision_run,case['case_id'],case['case_revision'],case['etag'],
                    'approve','synthetic-test-reviewer',client_idempotency_key='synthetic-test-approval-1')
    except StaleDecision:
        check('replay_rejected_no_duplicate',snapshot()==before)
    else:
        raise AssertionError('Resolved-case replay unexpectedly accepted')
    replay_code = '''import sys,json
from pathlib import Path
sys.dont_write_bytecode=True
sys.path.insert(0,sys.argv[1]+'/scripts')
from librarian.decisions import decide_case,StaleDecision
from librarian.runs import RunRecorder
root=Path(sys.argv[2]);case=json.loads(sys.argv[3]);run=json.loads(sys.argv[4])
try:
    decide_case(root,RunRecorder(root,run),case['case_id'],case['case_revision'],case['etag'],
                'approve','synthetic-test-reviewer',client_idempotency_key='synthetic-test-approval-1')
except StaleDecision:
    print('stale replay rejected')
else:
    raise SystemExit('Replay accepted')
'''
    replay = subprocess.run([sys.executable,'-c',replay_code,str(engine),str(root),
        json.dumps(case),json.dumps(decision_run.run)],capture_output=True,text=True,check=True)
    check('replay_after_process_restart',replay.stdout.strip()=='stale replay rejected' and snapshot()==before)
    receipts = load_receipts(root)
    check('receipt_hash_integrity',len(receipts)==3 and all(r['content_sha256']==
        content_sha256({k:v for k,v in r.items() if k!='content_sha256'}) for r in receipts.values()))
    check('no_incomplete_happy_path',not incomplete_transactions(root))
    probe = root/'Wiki/recovery-probe.txt'
    recovery = []
    for phase in ('prepared','files_applied','backup_recorded'):
        probe.write_text('before')
        run = recorder('Synthetic crash '+phase)
        try:
            apply_transaction(root,run.run_id,[{'operation':'replace','path':'Wiki/recovery-probe.txt',
                'base_sha256':file_sha256(probe),'content':'after'}],fail_after_phase=phase)
        except InjectedCrash:
            pass
        else:
            raise AssertionError('Crash injection not triggered')
        recovered = recover_transaction(root,run.run_id)
        check('recover_'+phase,recovered['phase']=='recovered' and probe.read_text()=='before')
        check('recovery_retry_'+phase,recover_transaction(root,run.run_id)==recovered)
        recovery.append(recovered)
    # Simulate crash after terminal receipt but before final response/finalization.
    run = recorder('Synthetic terminal-receipt recovery')
    cp = apply_transaction(root,run.run_id,[{'operation':'replace','path':'Wiki/recovery-probe.txt',
        'base_sha256':file_sha256(probe),'content':'committed-test'}],defer_finalize=True)
    run.finalize('pass',[],affected_paths=['Wiki/recovery-probe.txt'],
                 transaction=dict(cp,phase='finalized'))
    done = recover_transaction(root,run.run_id)
    check('recover_from_terminal_receipt',done['phase']=='finalized' and
        done['recovery_action']=='finished_from_terminal_receipt' and probe.read_text()=='committed-test')
    recovery.append(done)
    check('no_incomplete_recovered',not incomplete_transactions(root))
    # Keep a deliberately conflicted recovery case in a second synthetic instance.
    conflict_root=output/'conflict-instance'
    shutil.copytree(root,conflict_root)
    conflict_probe=conflict_root/'Wiki/recovery-probe.txt'
    run=RunRecorder.start(conflict_root,'Synthetic recovery conflict',mode='review-first')
    try:
        apply_transaction(conflict_root,run.run_id,[{'operation':'replace','path':'Wiki/recovery-probe.txt',
            'base_sha256':file_sha256(conflict_probe),'content':'interrupted'}],fail_after_phase='files_applied')
    except InjectedCrash:
        pass
    conflict_probe.write_text('concurrent synthetic edit')
    try:
        recover_transaction(conflict_root,run.run_id)
    except RecoveryConflict:
        check('recovery_conflict_preserved',conflict_probe.read_text()=='concurrent synthetic edit')
    else:
        raise AssertionError('Recovery overwrote concurrent edit')
    save('recovery.json',recovery)
    report={'status':'passed','synthetic_only':True,'approval':'simulated, not authenticated',
        'output':str(output),'engine_revision':json.loads((engine/'SOURCE_MANIFEST.json').read_text())['source_revision'],
        'network_namespace':current_ns,'host_network_namespace':host_ns,
        'git':'disabled in test instance; no authenticated Git checkout or startup claimed',
        'passed':passed,'not_run':['authenticated chat approval','production bootstrap/preflight',
        'semantic model synthesis','full acceptance suite','multi-writer fencing','device sync'],
        'limits':['Actor heuristic and optional upstream ETag are not human authentication.',
        'Replay is rejected as stale, not returned as the original receipt.',
        'Recovery probe tests exercise the canonical transaction layer on synthetic fixture files.',
        'Legacy typed proposal fixture supplies draft content; it is not autonomous source synthesis.']}
    save('test-report.json',report)
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':
    main()
