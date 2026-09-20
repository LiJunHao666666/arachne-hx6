import importlib.util,json,subprocess,sys
from pathlib import Path
import pytest
P=Path(__file__).resolve().parents[1]/'hexa_channel_state.py';S=importlib.util.spec_from_file_location('channel',P);M=importlib.util.module_from_spec(S);sys.modules[S.name]=M;S.loader.exec_module(M)
def packet(n=1,t=0,mode='CHANNEL_TEST',c=None):return {'schema_version':1,'sequence':n,'sim_time_s':t,'mode':mode,'motor_command':c if c is not None else [.25,0,0,0,0,0]}
@pytest.mark.parametrize('p,r',[(packet(c=[0]),'invalid_command_length'),(packet(c=[-1,0,0,0,0,0]),'command_out_of_range'),(packet(c=[float('nan'),0,0,0,0,0]),'non_finite_command'),(packet(c=[.1,.1,0,0,0,0]),'channel_test_requires_one_nonzero')])
def test_fail_closed(p,r):
 s=M.State();assert s.apply(p,0)['rejection_reason']==r;assert s.command==M.ZERO
def test_stop_timeout_reset():
 s=M.State();assert s.apply(packet(),0)['result']=='ACCEPTED';s.apply(packet(2,.1,'STOP',[0]*6),.1);assert s.apply(packet(3,.2),.2)['rejection_reason']=='stop_latched';s.reset(.21);assert s.state=='IDLE'
 t=M.State();t.apply(packet(),0);assert t.tick(.25)is None;assert t.tick(.251)['rejection_reason']=='link_timeout'
def test_time_checks():
 assert M.State().apply(packet(),.3)['rejection_reason']=='expired_command';assert M.State().apply(packet(t=1),0)['rejection_reason']=='future_command'
def test_cli(tmp_path):
 o=tmp_path/'r.json';x=subprocess.run([sys.executable,str(P),'--output',str(o)],capture_output=True,text=True);assert x.returncode==0
 r=json.loads(o.read_text());assert r['status']=='ANALYSIS_ONLY';assert r['procurement_allowed'] is False;assert [e['result'] for e in r['events']]==['ACCEPTED','ACCEPTED','STOPPED','REJECTED','RESET']
