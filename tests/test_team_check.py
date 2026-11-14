from pathlib import Path
import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1] / 'skills' / 'master-team'
spec=importlib.util.spec_from_file_location('team_check',ROOT/'scripts/team_check.py')
team=importlib.util.module_from_spec(spec)
spec.loader.exec_module(team)

def fixture():
    r=team.load(ROOT/'assets/worker_sessions.json')
    r.update(active_master_thread_id='master-1',generation=1,handoff_status='none')
    r['workers']['implementer']={'session_id':'worker-1','host_id':None,'role':'Implementer',
        'session_kind':'manual','transport':'user_file','parent_session_id':None,
        'verified':True,'active_ticket':{'ticket_id':'T1','attempt_id':'A1'}}
    a={'master_session_id':'master-1','master_generation':1,'worker_id':'implementer',
       'candidate_ref':'candidate-1','goal':'Implement scoped change','reads':['spec.md'],
       'writes':['src/feature'],'depends_on':[],'delivery':'pending_delivery',
       'execution':'planned','runtime':'unknown','acceptance':'pending','report_ref':None}
    r['tickets']['T1']={'task_id':'TASK1','current_attempt':'A1','attempts':{'A1':a}}
    r['write_claims']=[{'ticket_id':'T1','attempt_id':'A1','path':'src/feature'}]
    e={'task_id':'TASK1','ticket_id':'T1','attempt_id':'A1','master_session_id':'master-1',
       'master_generation':1,'worker_id':'implementer','worker_session_id':'worker-1',
       'candidate_ref':'candidate-1','goal':a['goal'],'reads':a['reads'][:],
       'writes':a['writes'][:],'record_ref':'tasks/TASK1.md#T1-A1'}
    return r,e

def running_fixture():
    r,e=fixture()
    a=r['tickets']['T1']['attempts']['A1']
    a.update(delivery='acknowledged',execution='running',runtime='running')
    result={'task_id':'TASK1','ticket_id':'T1','attempt_id':'A1','master_generation':1,
        'candidate_ref':'candidate-1','status':'done','summary':'Ready for acceptance',
        'artifacts':['src/feature/a.txt'],'checks':{'passed':['scoped test'],'failed':[],'not_run':[]},
        'report_ref':'reports/T1-A1.md'}
    return r,result

def second_attempt(r, path='src/other'):
    worker=copy.deepcopy(r['workers']['implementer'])
    worker.update(session_id='worker-2',active_ticket={'ticket_id':'T2','attempt_id':'A1'})
    r['workers']['reviewer']=worker
    a=copy.deepcopy(r['tickets']['T1']['attempts']['A1'])
    a.update(worker_id='reviewer',writes=[path],depends_on=[])
    r['tickets']['T2']={'task_id':'TASK1','current_attempt':'A1','attempts':{'A1':a}}
    r['write_claims'].append({'ticket_id':'T2','attempt_id':'A1','path':path})
    return a

class ProtocolTests(unittest.TestCase):
    def test_blank_template_valid_without_fictitious_workers(self):
        r=team.load(ROOT/'assets/worker_sessions.json')
        self.assertEqual(team.validate_registry(r),[])
        self.assertEqual(r['workers'],{})

    def test_registered_dispatch_valid(self):
        r,e=fixture(); self.assertEqual(team.validate_dispatch(r,e),[])

    def test_old_master_rejected(self):
        r,e=fixture(); e['master_session_id']='old-master'
        self.assertTrue(team.validate_dispatch(r,e))

    def test_old_generation_rejected(self):
        r,e=fixture(); e['master_generation']=0
        self.assertTrue(team.validate_dispatch(r,e))

    def test_frozen_scope_and_candidate_cannot_change(self):
        for field,value in [('writes',['src/expanded']),('candidate_ref','candidate-2'),('goal','new goal')]:
            with self.subTest(field=field):
                r,e=fixture(); e[field]=value
                self.assertTrue(team.validate_dispatch(r,e))

    def test_unknown_delivery_not_resent(self):
        r,e=fixture(); r['tickets']['T1']['attempts']['A1']['delivery']='unknown'
        self.assertTrue(team.validate_dispatch(r,e))

    def test_overlap_directory_and_case_insensitive_alias_rejected(self):
        for path in ['src/feature/a.py','SRC/Feature','src']:
            with self.subTest(path=path):
                r,e=fixture(); second_attempt(r,path)
                self.assertTrue(team.validate_registry(r))

    def test_distinct_scopes_can_coexist(self):
        r,e=fixture(); second_attempt(r,'src/feature-two')
        self.assertEqual(team.validate_registry(r),[])

    def test_unknown_runtime_keeps_claim(self):
        r,e=fixture(); r['write_claims']=[]
        self.assertTrue(team.validate_registry(r))

    def test_accepted_without_ended_runtime_still_keeps_claim(self):
        r,result=running_fixture(); a=r['tickets']['T1']['attempts']['A1']
        a.update(execution='submitted',acceptance='accepted',runtime='unknown',report_ref=result['report_ref'])
        r['write_claims']=[]
        self.assertTrue(team.validate_registry(r))

    def test_ended_runtime_can_release_claim(self):
        r,result=running_fixture(); a=r['tickets']['T1']['attempts']['A1']
        a.update(execution='submitted',acceptance='accepted',runtime='ended',report_ref=result['report_ref'])
        r['write_claims']=[]; r['workers']['implementer']['active_ticket']=None
        self.assertEqual(team.validate_registry(r),[])

    def test_acceptance_cannot_precede_submission(self):
        r,e=fixture(); r['tickets']['T1']['attempts']['A1']['acceptance']='accepted'
        self.assertTrue(team.validate_registry(r))

    def test_dependency_must_be_accepted(self):
        r,e=fixture(); a=second_attempt(r)
        a['depends_on']=[{'ticket_id':'T1','attempt_id':'A1'}]
        e.update(ticket_id='T2',worker_id='reviewer',worker_session_id='worker-2',writes=a['writes'])
        self.assertTrue(team.validate_dispatch(r,e))

    def test_dependency_cycle_rejected(self):
        r,e=fixture(); a=second_attempt(r)
        a['depends_on']=[{'ticket_id':'T1','attempt_id':'A1'}]
        r['tickets']['T1']['attempts']['A1']['depends_on']=[{'ticket_id':'T2','attempt_id':'A1'}]
        self.assertTrue(any('cycle' in err for err in team.validate_registry(r)))

    def test_parent_control_not_transferable_by_registry(self):
        r,e=fixture(); r['workers']['implementer'].update(session_kind='child',parent_session_id='other-parent')
        self.assertTrue(team.validate_dispatch(r,e))

    def test_wrong_recipient_rejected(self):
        r,e=fixture(); e['worker_session_id']='other-worker'
        self.assertTrue(team.validate_dispatch(r,e))

    def test_running_result_valid(self):
        r,result=running_fixture(); self.assertEqual(team.validate_result(r,result),[])

    def test_stopped_result_requires_host_end_confirmation(self):
        r,result=running_fixture();result['status']='stopped'
        self.assertTrue(team.validate_result(r,result))

    def test_stopped_result_allowed_after_host_end_confirmation(self):
        r,result=running_fixture();result['status']='stopped'
        r['tickets']['T1']['attempts']['A1'].update(execution='blocked',runtime='ended')
        self.assertEqual(team.validate_result(r,result),[])

    def test_handoff_requires_nonempty_evidence(self):
        r,result=running_fixture()
        r.update(active_master_thread_id='master-2',previous_master_thread_id='master-1',generation=2,handoff_status='completed')
        r['handoff']={'from_session_id':'master-1','to_session_id':'master-2','source_generation':1,
            'quiescence_evidence':'','transferred_by':'master-1','completed_at':'2026-11-14'}
        self.assertTrue(team.validate_registry(r))

    def test_result_before_recorded_start_not_accepted(self):
        r,e=fixture(); _,result=running_fixture()
        self.assertTrue(team.validate_result(r,result))

    def test_old_attempt_does_not_complete_new_attempt(self):
        r,result=running_fixture(); old=r['tickets']['T1']['attempts']['A1']
        old.update(execution='submitted',runtime='ended',acceptance='rejected',report_ref=result['report_ref'])
        new=copy.deepcopy(old); new.update(execution='planned',runtime='unknown',acceptance='pending',report_ref=None)
        r['tickets']['T1']['attempts']['A2']=new; r['tickets']['T1']['current_attempt']='A2'
        r['workers']['implementer']['active_ticket']['attempt_id']='A2'
        r['write_claims'][0]['attempt_id']='A2'
        self.assertTrue(team.validate_result(r,result))

    def test_result_candidate_and_generation_must_match(self):
        for field,value in [('candidate_ref','candidate-2'),('master_generation',2)]:
            with self.subTest(field=field):
                r,result=running_fixture(); result[field]=value
                self.assertTrue(team.validate_result(r,result))

    def test_inherited_running_result_keeps_original_generation(self):
        r,result=running_fixture()
        r.update(active_master_thread_id='master-2',previous_master_thread_id='master-1',generation=2,handoff_status='completed')
        r['handoff']={'from_session_id':'master-1','to_session_id':'master-2','source_generation':1,
            'quiescence_evidence':'reports/quiesced.md','transferred_by':'master-1','completed_at':'2026-11-14'}
        self.assertEqual(team.validate_result(r,result),[])

    def test_incomplete_handoff_blocks_dispatch(self):
        r,e=fixture(); r.update(handoff_status='quiescing',handoff={})
        self.assertTrue(team.validate_dispatch(r,e))

    def test_repeated_result_same_candidate_is_read_only(self):
        r,result=running_fixture(); a=r['tickets']['T1']['attempts']['A1']
        a.update(execution='submitted',report_ref=result['report_ref'])
        before=copy.deepcopy(r)
        self.assertEqual(team.validate_result(r,result),[])
        self.assertEqual(r,before)
        result['report_ref']='reports/changed.md'
        self.assertTrue(team.validate_result(r,result))

    def test_unsafe_paths_rejected(self):
        for path in ['../secrets','C:/outside','/outside','src/**/*.py','src/name.','src/name ']:
            with self.subTest(path=path):
                with self.assertRaises(ValueError): team.normalize_path(path)

    def test_utf8_bytes_and_hard_limit(self):
        with tempfile.TemporaryDirectory() as temp:
            file=Path(temp)/'message.txt'; file.write_bytes('中文\r\n'.encode())
            info=team.message_size(file,budget=4,hard_limit=7)
            self.assertEqual(info['bytes'],8)
            self.assertTrue(info['over_budget']); self.assertTrue(info['over_hard_limit'])

    def test_v1_migration_preserves_identity_and_unresolved(self):
        old={'schema_version':1,'active_master_thread_id':'master-1','generation':4,
            'workers':{'DevCoder':{'thread_id':'worker-1','active_ticket':'old-ticket'}},
            'tickets':{'old-ticket':{'custom':'keep'}},'custom_extension':'keep'}
        before=copy.deepcopy(old); new=team.migrate_v1(old)
        self.assertEqual(old,before)
        self.assertEqual(new['workers']['DevCoder']['session_id'],'worker-1')
        self.assertEqual(new['legacy_v1']['custom_extension'],'keep')
        self.assertTrue(new['migration_unresolved'])
        self.assertTrue(team.validate_registry(new))

    def test_migration_cli_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp)/'old.json'; dest=Path(temp)/'new.json'
            source.write_text(json.dumps({'schema_version':1,'workers':{},'tickets':{}}),encoding='utf-8')
            args=[sys.executable,str(ROOT/'scripts/team_check.py'),'migrate','--input',str(source),'--output',str(dest)]
            first=subprocess.run(args,capture_output=True)
            self.assertEqual(first.returncode,0,first.stderr)
            original=dest.read_bytes()
            again=subprocess.run(args,capture_output=True)
            self.assertEqual(again.returncode,2)
            self.assertEqual(dest.read_bytes(),original)

if __name__=='__main__': unittest.main(verbosity=2)
