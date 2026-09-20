import importlib.util,json,math,subprocess,sys
from pathlib import Path
import pytest
P=Path(__file__).resolve().parents[1]/'hexa_attitude_flight.py';S=importlib.util.spec_from_file_location('attitude',P);M=importlib.util.module_from_spec(S);sys.modules[S.name]=M;S.loader.exec_module(M)
def test_allocator_reconstructs_wrench():
 p=M.Parameters();a=M.allocation_matrix(p);pinv=M.pseudoinverse(a);wanted=[p.mass_kg*p.gravity_m_s2,.01,-.02,.003];got=M.matvec(a,M.matvec(pinv,wanted));assert got==pytest.approx(wanted,abs=1e-10)
def test_geometry_and_rotation_are_symmetric():
 a=M.allocation_matrix(M.Parameters());assert a[0]==[1]*6;assert sum(a[1])==pytest.approx(0,abs=1e-12);assert sum(a[2])==pytest.approx(0,abs=1e-12);assert sum(a[3])==pytest.approx(0,abs=1e-12)
def test_attitude_converges_without_saturation():
 r=M.simulate();assert r['scenario_result']=='PASS';assert max(r['metrics']['final_abs_angles_deg'])<=.5;assert r['metrics']['saturated_channel_steps']==0;assert r['flight_readiness']=='UNDETERMINED'
def test_all_six_channels_stay_in_bounds():
 r=M.simulate();limit=r['parameters']['max_thrust_per_rotor_n']
 assert all(len(s['rotor_thrust_n'])==6 and all(0<=x<=limit for x in s['rotor_thrust_n']) for s in r['samples'])
@pytest.mark.parametrize('kwargs',[{'arm_m':0},{'inertia_x_kg_m2':float('nan')},{'max_thrust_per_rotor_n':1.0}])
def test_invalid_parameters(kwargs):
 with pytest.raises(ValueError):M.simulate(M.Parameters(**kwargs))
def test_deterministic_cli(tmp_path):
 assert M.simulate()==M.simulate();o=tmp_path/'a.json';x=subprocess.run([sys.executable,str(P),'--output',str(o)],capture_output=True,text=True);assert x.returncode==0,x.stderr
 r=json.loads(o.read_text());assert r['status']=='ANALYSIS_ONLY';assert r['scope']=='SMALL_ANGLE_ATTITUDE_ONLY'
