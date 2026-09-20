import importlib.util,json,subprocess,sys
from pathlib import Path
import pytest
P=Path(__file__).resolve().parents[1]/'hexa_vertical_flight.py';S=importlib.util.spec_from_file_location('flight',P);M=importlib.util.module_from_spec(S);sys.modules[S.name]=M;S.loader.exec_module(M)
def test_default_takeoff_hover_land_passes():
 r=M.simulate();assert r['scenario_result']=='PASS';assert r['scope']=='VERTICAL_AXIS_ONLY';assert r['metrics']['landed'];assert r['metrics']['hover_rmse_m']<=r['criteria']['hover_rmse_m_max'];assert r['flight_readiness']=='UNDETERMINED'
def test_six_equal_rotor_outputs_and_bounds():
 r=M.simulate();limit=r['parameters']['max_thrust_per_rotor_n']
 for sample in r['samples']:
  assert len(sample['rotor_thrust_n'])==6;assert max(sample['rotor_thrust_n'])==pytest.approx(min(sample['rotor_thrust_n']));assert 0<=sample['rotor_thrust_n'][0]<=limit
@pytest.mark.parametrize('kwargs',[{'mass_kg':0},{'dt_s':float('nan')},{'max_thrust_per_rotor_n':1.0}])
def test_invalid_parameters(kwargs):
 with pytest.raises(ValueError):M.simulate(M.Parameters(**kwargs))
def test_deterministic_and_cli(tmp_path):
 assert M.simulate()==M.simulate();out=tmp_path/'flight.json';x=subprocess.run([sys.executable,str(P),'--output',str(out)],capture_output=True,text=True);assert x.returncode==0,x.stderr
 r=json.loads(out.read_text());assert r['status']=='ANALYSIS_ONLY';assert r['procurement_allowed'] is False
