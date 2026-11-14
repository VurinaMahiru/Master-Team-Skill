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

def fresh(): return team.load(ROOT/'assets/onboarding_state.json')

def underway():
    state=fresh()
    state.update(status='in_progress',current_step='roles',completed_steps=['purpose','environment'],
                 project_root=r'D:\Example',learner_scope='learner-a')
    return state

class OnboardingTests(unittest.TestCase):
    def test_first_use_starts_without_extra_opt_in(self):
        decision=team.onboarding_decision(fresh())
        self.assertEqual((decision['route'],decision['step']),('start','purpose'))
        self.assertFalse(decision['team_actions_authorized'])

    def test_resume_preserves_cursor_without_reasking_previous_steps(self):
        state=underway()
        decision=team.onboarding_decision(state)
        self.assertEqual((decision['route'],decision['step']),('resume','roles'))

    def test_pause_and_dismiss_do_not_auto_restart(self):
        for status in ('paused','dismissed'):
            with self.subTest(status=status):
                state=underway();state['status']=status
                self.assertEqual(team.onboarding_decision(state)['route'],'no_auto_lesson')

    def test_disabled_auto_start_still_allows_explicit_resume(self):
        state=underway();state['auto_start']=False
        self.assertEqual(team.onboarding_decision(state)['route'],'no_auto_lesson')
        self.assertEqual(team.onboarding_decision(state,action='resume')['step'],'roles')

    def test_concrete_task_takes_priority_over_pending_lesson(self):
        self.assertEqual(team.onboarding_decision(underway(),concrete_task=True)['route'],'task')

    def test_existing_team_is_not_reinitialized(self):
        self.assertEqual(team.onboarding_decision(fresh(),existing_team=True)['route'],'task')
        state=underway();state['context']['team_exists']=True
        self.assertEqual(team.onboarding_decision(state)['route'],'task')

    def test_maintenance_never_starts_teaching(self):
        decision=team.onboarding_decision(fresh(),action='maintenance')
        self.assertEqual(decision['route'],'maintenance')

    def test_invalid_progress_does_not_block_maintenance(self):
        decision=team.onboarding_decision({},action='maintenance')
        self.assertEqual(decision['route'],'maintenance')
        self.assertTrue(decision['ok'])

    def test_invalid_progress_does_not_block_explicit_task(self):
        decision=team.onboarding_decision({},concrete_task=True)
        self.assertEqual(decision['route'],'task')
        self.assertTrue(decision['preserve_old_state'])

    def test_unbound_progress_does_not_block_explicit_task(self):
        state=underway();state['project_root']=None
        decision=team.onboarding_decision(state,concrete_task=True,project_root=r'D:\Example')
        self.assertEqual(decision['route'],'task')
        self.assertTrue(decision['preserve_old_state'])

    def test_schema_version_cannot_be_boolean(self):
        state=fresh();state['schema_version']=True
        self.assertTrue(team.validate_onboarding(state))

    def test_pause_does_not_cancel_runtime(self):
        decision=team.onboarding_decision(underway(),action='pause')
        self.assertEqual(decision['suggested_status'],'paused')
        self.assertFalse(decision['team_actions_authorized'])

    def test_skip_all_does_not_claim_course_completed(self):
        decision=team.onboarding_decision(underway(),action='skip_all')
        self.assertEqual((decision['route'],decision['suggested_status']),('task','dismissed'))

    def test_restart_keeps_automatic_teaching_preference(self):
        state=underway();state['auto_start']=False
        snapshot=copy.deepcopy(state)
        decision=team.onboarding_decision(state,action='restart')
        self.assertEqual(decision['step'],'purpose')
        self.assertTrue(decision['preserve_auto_start_preference'])
        self.assertEqual(state,snapshot)

    def test_different_project_does_not_inherit_pause_or_goal(self):
        state=underway();state.update(status='paused',auto_start=False)
        decision=team.onboarding_decision(state,project_root=r'D:\Other')
        self.assertEqual(decision['route'],'new_scope_start')
        self.assertTrue(decision['preserve_old_state'])

    def test_different_learner_does_not_inherit_progress(self):
        decision=team.onboarding_decision(underway(),learner_scope='learner-b')
        self.assertEqual((decision['route'],decision['step']),('new_scope_start','purpose'))

    def test_disable_in_other_scope_does_not_overwrite_old_scope(self):
        state=underway();snapshot=copy.deepcopy(state)
        decision=team.onboarding_decision(state,action='disable',learner_scope='learner-b')
        self.assertEqual(decision['route'],'new_scope_task')
        self.assertTrue(decision['preserve_old_state'])
        self.assertFalse(decision['suggested_auto_start'])
        self.assertEqual(state,snapshot)

    def test_windows_path_aliases_reuse_same_scope(self):
        decision=team.onboarding_decision(underway(),project_root='d:/example/',learner_scope='learner-a')
        self.assertEqual(decision['route'],'resume')

    def test_unbound_old_progress_is_not_assumed_to_belong_to_user(self):
        state=underway();state['learner_scope']=None
        decision=team.onboarding_decision(state,learner_scope='learner-a')
        self.assertEqual(decision['route'],'scope_unverified')

    def test_skill_upgrade_does_not_reset_completed_course(self):
        state=fresh();state.update(status='completed',current_step='finished',
            completed_steps=list(team.ONBOARDING_STEPS),skill_version='2.0.0')
        self.assertEqual(team.onboarding_decision(state)['route'],'no_auto_lesson')

    def test_completion_requires_all_steps(self):
        state=underway();state.update(status='completed',current_step='finished')
        self.assertTrue(team.validate_onboarding(state))

    def test_pause_after_completion_keeps_valid_completed_state(self):
        state=fresh();state.update(status='completed',current_step='finished',
            completed_steps=list(team.ONBOARDING_STEPS))
        for action in ('pause','skip_all'):
            with self.subTest(action=action):
                decision=team.onboarding_decision(state,action=action)
                self.assertEqual(decision['route'],'no_auto_lesson')
                self.assertNotIn('suggested_status',decision)

    def test_skipped_and_completed_are_distinct(self):
        state=underway();state['skipped_steps']=['purpose']
        self.assertTrue(team.validate_onboarding(state))
        state=fresh();state.update(status='completed',current_step='finished',
            completed_steps=['purpose','environment','roles','first_task'],skipped_steps=['setup','practice'])
        self.assertEqual(team.validate_onboarding(state),[])

    def test_cli_is_read_only_and_does_not_initialize_team(self):
        with tempfile.TemporaryDirectory() as temp:
            directory=Path(temp);file=directory/'progress.json'
            file.write_text(json.dumps(underway()),encoding='utf-8')
            original=file.read_bytes()
            process=subprocess.run([sys.executable,'-X','utf8','-B',str(ROOT/'scripts/team_check.py'),
                'onboarding','--state',str(file),'--action','resume'],capture_output=True,text=True,encoding='utf-8')
            self.assertEqual(process.returncode,0,process.stderr)
            self.assertEqual(json.loads(process.stdout)['step'],'roles')
            self.assertEqual(file.read_bytes(),original)
            self.assertEqual([p.name for p in directory.iterdir()],['progress.json'])

if __name__=='__main__':unittest.main(verbosity=2)
