import json
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

from lab_automation import local_observation as o


def job():
    return {'job_id':o.JOB_ID,'lab':'math_lab','branch':o.BASE,'execution_mode':o.MODE,
            'goal':'inventory','authority_refs':o.profile()['authority_refs'],'expected_outputs':[],
            'allowed_write_paths':[o.SCOPE],'db_access':'read_only','network_policy':'restricted',
            'destructive_actions_allowed':False,'parent_job_ids':['SV-MATH-DP-OBSERVATION-002'],
            'parent_run_id':o.FAILED_RUN,'status':'queued'}


def result(run_id):
    return {'job_id':o.JOB_ID,'run_id':run_id,'schema_version':'daily-price-readiness-result/0.3',
            'status':'partial','inventory_permission':{'status':'permitted_read_only','implies_research_input_eligibility':False},
            'probe':{'extraction_version':o.BASE,'database_status':'available',
                'database_target':'postgresql://synthetic/db','read_only_verified':True,
                'read_only_evidence':{'transaction_read_only':True,'transaction_isolation':'repeatable read'}},
            'findings':{'representative_basket':[{'symbol':s,'research_input_sufficiency':'unassessed'}
                for s in ['SPY','AAPL','JPM','XOM','WMT','UNH']],
                'data_eligibility_decisions':[{'research_input_sufficiency':'unassessed',
                    'research_input_permitted':False,'permitted_symbols':[]}]}}


@pytest.mark.parametrize('field,value',[
    ('branch','other'),('lab','research_lab'),('db_access','read_write'),
    ('allowed_write_paths',['math_lab']),('parent_run_id','old'),
    ('codex_command',['sh','-c','arbitrary']),('test_commands',[['arbitrary']]),
    ('command',['arbitrary']),('execution_mode','other')])
def test_unapproved_job_rejected(field,value):
    raw=job();raw[field]=value
    with pytest.raises(ValueError): o.check_job(raw)


def test_fixed_profile_accepted(): o.check_job(job())


def test_env_boundary():
    source={'PATH':'/bin','HOME':'/synthetic','DB_PASSWORD':'synthetic','PGPASSWORD':'synthetic',
            'STOCKVIS_LAB_DB_PASSWORD':'synthetic2','DATABASE_URL':'synthetic',
            'PYTHONPATH':'evil','BASH_ENV':'evil','DYLD_INSERT_LIBRARIES':'evil','CODEX_HOME':'/model-auth'}
    host=o.host_environment(source);review=o.review_environment(source)
    assert host['DB_PASSWORD']=='synthetic2'
    assert set(review)=={'PATH','HOME','CODEX_HOME'}
    assert not {'PYTHONPATH','BASH_ENV','DYLD_INSERT_LIBRARIES'} & host.keys()


def test_isolated_review_home_references_auth_without_user_config(tmp_path):
    home=tmp_path/'home';codex_home=home/'.codex';codex_home.mkdir(parents=True)
    auth=codex_home/'auth.json';auth.write_text('{"synthetic":"credential"}')
    (codex_home/'config.toml').write_text('[mcp_servers.existing]\ncommand="unsafe"')
    env,isolated,linked=o.isolated_review_environment({'PATH':'/bin','HOME':str(home)},tmp_path/'state',str(uuid4()))
    assert linked is True and Path(env['CODEX_HOME'])==isolated
    assert (isolated/'auth.json').is_symlink() and (isolated/'auth.json').resolve()==auth
    assert not (isolated/'config.toml').exists()


def test_output_and_argument_allowlist(tmp_path):
    run=str(uuid4());output=tmp_path/o.SCOPE/run
    command=o.probe_command(tmp_path,output,run)
    assert '--job-id' in command and command[command.index('--job-id')+1]==o.JOB_ID
    assert '-I' in command and '-B' in command
    with pytest.raises(ValueError):o.probe_command(tmp_path,tmp_path/'elsewhere',run)
    with pytest.raises(ValueError):o.probe_command(tmp_path,output,'old-run')


def test_probe_hash_and_extra_code_rejected(tmp_path,monkeypatch):
    p=tmp_path/'math_lab/runtime/x.py';p.parent.mkdir(parents=True);p.write_text('safe')
    monkeypatch.setattr(o,'profile',lambda:{'files':{'math_lab/runtime/x.py':o.digest(p)}})
    o.verify_probe(tmp_path)
    (p.parent/'unexpected.py').write_text('evil')
    with pytest.raises(ValueError):o.verify_probe(tmp_path)


def test_changed_probe_rejected(tmp_path,monkeypatch):
    p=tmp_path/'math_lab/runtime/x.py';p.parent.mkdir(parents=True);p.write_text('safe');sha=o.digest(p)
    monkeypatch.setattr(o,'profile',lambda:{'files':{'math_lab/runtime/x.py':sha}})
    p.write_text('changed')
    with pytest.raises(ValueError):o.verify_probe(tmp_path)


def test_seal_tamper_and_symlink_rejected(tmp_path):
    p=tmp_path/'result.json';p.write_text('{}');h={'result.json':o.digest(p)}
    o.verify_seal(tmp_path,h);p.write_text('[]')
    with pytest.raises(ValueError):o.verify_seal(tmp_path,h)
    p.unlink();(tmp_path/'other').write_text('{}');p.symlink_to(tmp_path/'other')
    with pytest.raises(ValueError):o.verify_seal(tmp_path,h)


@pytest.mark.parametrize('defect',['query','read_only','isolation','permission','sufficiency','symbols','identity'])
def test_invalid_observation_rejected(defect):
    run=str(uuid4());r=result(run)
    if defect=='query':r['probe']['database_status']='query_failed'
    if defect=='read_only':r['probe']['read_only_verified']=False
    if defect=='isolation':r['probe']['read_only_evidence']['transaction_isolation']='read committed'
    if defect=='permission':r['findings']['data_eligibility_decisions'][0]['research_input_permitted']=True
    if defect=='sufficiency':r['findings']['representative_basket'][0]['research_input_sufficiency']='sufficient'
    if defect=='symbols':r['findings']['representative_basket'].pop()
    if defect=='identity':r['run_id']='wrong'
    with pytest.raises(ValueError):o.validate_observation(r,run)


@pytest.mark.parametrize('defect',['blocker','wrong_hash','empty','permission'])
def test_review_does_not_override_gate(defect):
    r={'run_id':'r','input_hashes':{'x':'hash'},'verdict':'pass','blockers':[],
       'limitations':[],'summary':'inventory only','research_input_sufficiency':'unassessed',
       'research_input_permitted':False}
    if defect=='blocker':r['blockers']=['inconsistent']
    if defect=='wrong_hash':r['input_hashes']={'x':'wrong'}
    if defect=='empty':r={}
    if defect=='permission':r['research_input_permitted']=True
    with pytest.raises(ValueError):o.check_review(r,'r',{'x':'hash'})


@pytest.mark.parametrize('failure',[None,'probe','review','blocker','commit'])
def test_orchestration_producers_failures_and_preservation(tmp_path,monkeypatch,failure):
    from lab_automation import local_runner as runner
    repo=tmp_path/'source';repo.mkdir();state=tmp_path/'state';worktrees=tmp_path/'worktrees'
    (state/'ledger').mkdir(parents=True)
    (state/'ledger'/(o.JOB_ID+'.jsonl')).write_text(json.dumps({
        'run_id':o.FAILED_003_RUN,'stage':'terminal','status':'failed'})+'\n')
    job_file=tmp_path/'job.json';job_file.write_text(json.dumps(job()))
    called=[];commits=[]
    monkeypatch.setattr(o,'verify_probe',lambda p:None)
    monkeypatch.setattr(o,'redactor',lambda p:lambda s,env:s.replace('synthetic-secret','[REDACTED]'))
    monkeypatch.setattr(o,'preflight_reviewer',lambda *a:{'verified':True,'command_prefix':o.review_prefix('/synthetic/codex')})
    monkeypatch.setattr(o,'isolated_review_environment',lambda env,state,run:(o.review_environment(env),tmp_path/'review-home',False))
    monkeypatch.setattr(o.shutil,'which',lambda x:'/synthetic/codex')
    monkeypatch.setattr(runner,'_changed_paths',lambda p:[])
    def git(cwd,*args,**kwargs):
        if args[:2]==('worktree','add'):Path(args[-2]).mkdir(parents=True)
        value=o.BASE if Path(cwd)!=repo or args[-1]==o.BASE else 'runner-sha'
        return SimpleNamespace(stdout=value+'\n',returncode=0)
    monkeypatch.setattr(runner,'_git',git)
    def commit(*args):
        commits.append(True)
        if failure=='commit':raise runner.CommandFailure({'stage':'candidate_commit','returncode':1,'stderr':'synthetic-secret','stdout':'','command':['git','commit']})
        return 'candidate-sha'
    monkeypatch.setattr(runner,'_candidate_commit',commit)
    def execute(command,**kwargs):
        called.append(command)
        if any('import pytest' in part for part in command):return SimpleNamespace(returncode=0,stdout='52 passed',stderr='')
        if '--job-id' in command:
            run=command[command.index('--run-id')+1]
            output=Path(command[command.index('--result-json')+1]);r=result(run)
            if failure=='probe':r['probe']['database_status']='unavailable'
            output.write_text(json.dumps(r));(output.parent/'data_gaps.json').write_text('[]');(output.parent/'agent_report.md').write_text('inventory')
            return SimpleNamespace(returncode=2 if failure=='probe' else 0,stdout='',stderr='synthetic-secret' if failure=='probe' else '')
        prompt=kwargs['input'];data=json.loads(prompt[prompt.index('\n')+1:])
        r={'run_id':data['run_id'],'input_hashes':data['input_hashes'],'verdict':'pass',
           'blockers':['blocker'] if failure=='blocker' else [],'limitations':[],
           'summary':'synthetic review','research_input_sufficiency':'unassessed','research_input_permitted':False}
        Path(command[command.index('--output-last-message')+1]).write_text(json.dumps(r))
        assert not any(k.startswith(('DB_','PG','STOCKVIS_LAB_DB')) for k in kwargs['env'])
        return SimpleNamespace(returncode=1 if failure=='review' else 0,stdout='',stderr='')
    monkeypatch.setattr(o.subprocess,'run',execute)
    rc=o.execute(repo,job_file,worktrees,state,False)
    assert rc==(0 if failure is None else 1)
    assert bool(commits)==(failure in (None,'commit'))
    evidence=next((state/'runs'/o.JOB_ID).iterdir())
    assert list(worktrees.iterdir()),'Worktree must be preserved even after failure'
    if failure=='probe': assert not (evidence/'codex_review_invocation.json').exists()
    if failure is None:
        a=json.loads((evidence/'local_observation_invocation.json').read_text());b=json.loads((evidence/'codex_review_invocation.json').read_text())
        assert a['actor']=='mac_local_executor' and b['actor']=='codex_reviewer'
        assert a['invocation_id']!=b['invocation_id'] and b['input_snapshot_ref']
    if failure=='commit':assert '[REDACTED]' in (evidence/'command_failure.json').read_text()
    for p in evidence.glob('*.json'):assert 'synthetic-secret' not in p.read_text()
    ledger=(state/'ledger'/(o.JOB_ID+'.jsonl')).read_text()
    assert 'observability_gap' in ledger and 'command_copy_paste' in ledger


def test_reviewer_enabled_tools_fail_closed(monkeypatch,tmp_path):
    monkeypatch.setattr(o.subprocess,'run',lambda *a,**k:SimpleNamespace(returncode=0,stdout='shell_tool stable true\nunified_exec stable false',stderr=''))
    with pytest.raises(ValueError):o.preflight_reviewer('codex',{},tmp_path)


def test_unified_exec_backend_does_not_imply_shell_tool_exposure(monkeypatch,tmp_path):
    def run(command,**kwargs):
        if 'features' in command:text='shell_tool stable false\nunified_exec stable true'
        elif 'mcp' in command:text='[]'
        elif 'login' in command:text='Logged in'
        else:text='--ephemeral --output-last-message --sandbox'
        return SimpleNamespace(returncode=0,stdout=text,stderr='')
    monkeypatch.setattr(o.subprocess,'run',run)
    settings=o.preflight_reviewer('codex',{},tmp_path)
    assert settings['shell_tool'] is False
    assert settings['unified_exec_backend_enabled'] is True


def test_reviewer_preflight_uses_validated_disable_flags_and_preserves_failure(monkeypatch,tmp_path):
    command=[]
    def run(argv,**kwargs):
        command.extend(argv)
        return SimpleNamespace(returncode=0,
            stdout='shell_tool stable true\nunified_exec stable false\n',stderr='diagnostic')
    monkeypatch.setattr(o.subprocess,'run',run)
    with pytest.raises(o.ReviewerPreflightError) as caught:
        o.preflight_reviewer('codex',{},tmp_path)
    assert command[:5]==['codex','--disable','shell_tool','--disable','unified_exec']
    assert caught.value.checks[0]['stdout'].startswith('shell_tool stable true')
    assert caught.value.checks[0]['stderr']=='diagnostic'


def test_existing_mcp_fails_closed_instead_of_rewriting_transport(monkeypatch,tmp_path):
    def run(command,**kwargs):
        if 'features' in command:text='shell_tool stable false\nunified_exec stable false'
        elif 'mcp' in command:text=json.dumps([{'name':'existing','enabled':True}])
        else:text='--ephemeral --output-last-message --sandbox'
        return SimpleNamespace(returncode=0,stdout=text,stderr='')
    monkeypatch.setattr(o.subprocess,'run',run)
    with pytest.raises(o.ReviewerPreflightError):o.preflight_reviewer('codex',{},tmp_path)


def test_empty_isolated_mcp_configuration_is_accepted(monkeypatch,tmp_path):
    calls=[]
    def run(command,**kwargs):
        calls.append(command)
        if 'features' in command:
            text='shell_tool stable false\nunified_exec stable true'
        elif 'mcp' in command:text='[]'
        elif 'login' in command:text='Logged in using ChatGPT'
        else:
            text='--ephemeral --output-last-message --sandbox'
        return SimpleNamespace(returncode=0,stdout=text,stderr='')
    monkeypatch.setattr(o.subprocess,'run',run)
    settings=o.preflight_reviewer('codex',{},tmp_path)
    assert settings['enabled_mcp_servers']==0
    assert len([c for c in calls if 'mcp' in c])==1
    assert len([c for c in calls if 'login' in c])==1
