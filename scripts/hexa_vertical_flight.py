#!/usr/bin/env python3
"""Deterministic vertical-axis closed-loop hexarotor simulation."""
import argparse
from dataclasses import dataclass,asdict
import json,math
from pathlib import Path

@dataclass(frozen=True)
class Parameters:
 mass_kg:float=.65
 gravity_m_s2:float=9.80665
 max_thrust_per_rotor_n:float=2.0
 actuator_tau_s:float=.08
 kp_n_per_m:float=7.0
 kd_n_per_m_s:float=4.0
 dt_s:float=.01
 duration_s:float=10.0

def validate(p):
 for name,value in asdict(p).items():
  if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value<=0:raise ValueError(f'{name} must be finite and positive')
 if 6*p.max_thrust_per_rotor_n<=p.mass_kg*p.gravity_m_s2:raise ValueError('maximum thrust must exceed weight')

def reference(t):
 if t<2:return .5*t,.5,'TAKEOFF'
 if t<6:return 1.0,0.0,'HOVER'
 if t<8:return 1.0-.5*(t-6),-.5,'LAND'
 return 0.0,0.0,'DISARMED'

def simulate(p=Parameters()):
 validate(p);z=v=thrust=0.0;samples=[];sat=0
 steps=round(p.duration_s/p.dt_s)
 for i in range(steps+1):
  t=i*p.dt_s;target,target_v,phase=reference(t)
  if phase=='DISARMED':requested=0.0
  else:requested=p.mass_kg*p.gravity_m_s2+p.kp_n_per_m*(target-z)+p.kd_n_per_m_s*(target_v-v)
  maximum=6*p.max_thrust_per_rotor_n;command=max(0.0,min(maximum,requested))
  sat+=int(command!=requested);thrust+=(command-thrust)*min(1.0,p.dt_s/p.actuator_tau_s)
  acceleration=thrust/p.mass_kg-p.gravity_m_s2
  v+=acceleration*p.dt_s;z+=v*p.dt_s
  if z<0:z=v=0.0
  samples.append({'time_s':t,'phase':phase,'target_altitude_m':target,'altitude_m':z,'vertical_speed_m_s':v,'total_thrust_n':thrust,'rotor_thrust_n':[thrust/6]*6})
 hover=[x['altitude_m']-1 for x in samples if 3<=x['time_s']<=6]
 landed=samples[-1]['altitude_m']<=.02 and abs(samples[-1]['vertical_speed_m_s'])<=.05
 metrics={'hover_rmse_m':math.sqrt(sum(x*x for x in hover)/len(hover)),'max_altitude_m':max(x['altitude_m'] for x in samples),'final_altitude_m':samples[-1]['altitude_m'],'final_vertical_speed_m_s':samples[-1]['vertical_speed_m_s'],'saturated_steps':sat,'landed':landed}
 passed=metrics['hover_rmse_m']<=.10 and metrics['max_altitude_m']<=1.20 and landed
 return {'schema_version':1,'status':'ANALYSIS_ONLY','procurement_allowed':False,'flight_readiness':'UNDETERMINED','scope':'VERTICAL_AXIS_ONLY','parameter_evidence':'PLANNING_ASSUMPTION','parameters':asdict(p),'criteria':{'hover_rmse_m_max':.10,'max_altitude_m_max':1.20,'final_altitude_m_max':.02,'final_speed_abs_m_s_max':.05},'metrics':metrics,'scenario_result':'PASS' if passed else 'FAIL','samples':samples,'limitations':['No attitude, horizontal motion, aerodynamics, battery, noise, estimator, or structural model','Equal rotor allocation is not a six-axis control allocator','Simulation pass does not prove physical flight readiness']}

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
 try:result=simulate()
 except ValueError as exc:parser.error(str(exc))
 args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
 print(f"Vertical scenario: {result['scenario_result']}; flight: UNDETERMINED");return 0 if result['scenario_result']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
