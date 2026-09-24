#!/usr/bin/env python3
"""Offline six-rotor attitude allocator and small-angle dynamics."""
import argparse,json,math
from dataclasses import dataclass,asdict
from pathlib import Path

@dataclass(frozen=True)
class Parameters:
 mass_kg:float=.65; gravity_m_s2:float=9.80665; arm_m:float=.12
 yaw_torque_per_thrust_m:float=.015; inertia_x_kg_m2:float=.004
 inertia_y_kg_m2:float=.004; inertia_z_kg_m2:float=.007
 max_thrust_per_rotor_n:float=2.0; kp_roll:float=.08; kd_roll:float=.025
 kp_pitch:float=.08; kd_pitch:float=.025; kp_yaw:float=.05; kd_yaw:float=.02
 dt_s:float=.005; duration_s:float=5.0

def invert(a):
 n=len(a);m=[list(row)+[float(i==j) for j in range(n)] for i,row in enumerate(a)]
 for c in range(n):
  pivot=max(range(c,n),key=lambda r:abs(m[r][c]))
  if abs(m[pivot][c])<1e-12:raise ValueError('singular allocation matrix')
  m[c],m[pivot]=m[pivot],m[c];d=m[c][c];m[c]=[x/d for x in m[c]]
  for r in range(n):
   if r!=c:
    f=m[r][c];m[r]=[x-f*y for x,y in zip(m[r],m[c])]
 return [row[n:] for row in m]

def allocation_matrix(p):
 rows=[[],[],[],[]]
 for i in range(6):
  angle=math.radians(30+60*i);x=p.arm_m*math.cos(angle);y=p.arm_m*math.sin(angle)
  rows[0].append(1.0);rows[1].append(y);rows[2].append(-x);rows[3].append((1 if i%2==0 else -1)*p.yaw_torque_per_thrust_m)
 return rows

def pseudoinverse(a):
 aat=[[sum(a[i][k]*a[j][k] for k in range(6)) for j in range(4)] for i in range(4)]
 inv=invert(aat)
 return [[sum(a[j][i]*inv[j][k] for j in range(4)) for k in range(4)] for i in range(6)]

def matvec(a,x):return [sum(v*w for v,w in zip(row,x)) for row in a]

def validate(p):
 for n,v in asdict(p).items():
  if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) or v<=0:raise ValueError(f'{n} must be finite and positive')
 if 6*p.max_thrust_per_rotor_n<=p.mass_kg*p.gravity_m_s2:raise ValueError('maximum thrust must exceed weight')

def simulate(p=Parameters()):
 validate(p);a=allocation_matrix(p);pinv=pseudoinverse(a)
 angles=[math.radians(8),math.radians(-5),math.radians(10)];rates=[0.,0.,0.]
 samples=[];saturated=0
 for i in range(round(p.duration_s/p.dt_s)+1):
  torques=[-p.kp_roll*angles[0]-p.kd_roll*rates[0],-p.kp_pitch*angles[1]-p.kd_pitch*rates[1],-p.kp_yaw*angles[2]-p.kd_yaw*rates[2]]
  requested=matvec(pinv,[p.mass_kg*p.gravity_m_s2]+torques)
  thrust=[max(0.,min(p.max_thrust_per_rotor_n,x)) for x in requested];saturated+=sum(x!=y for x,y in zip(thrust,requested))
  wrench=matvec(a,thrust);actual=wrench[1:]
  inertias=[p.inertia_x_kg_m2,p.inertia_y_kg_m2,p.inertia_z_kg_m2]
  for axis in range(3):rates[axis]+=actual[axis]/inertias[axis]*p.dt_s;angles[axis]+=rates[axis]*p.dt_s
  samples.append({'time_s':i*p.dt_s,'angles_deg':[math.degrees(x) for x in angles],'rates_deg_s':[math.degrees(x) for x in rates],'rotor_thrust_n':thrust,'requested_wrench':[p.mass_kg*p.gravity_m_s2]+torques,'actual_wrench':wrench})
 final=[abs(math.degrees(x)) for x in angles];peak=max(max(abs(v) for v in s['angles_deg']) for s in samples)
 metrics={'final_abs_angles_deg':final,'peak_abs_angle_deg':peak,'saturated_channel_steps':saturated}
 passed=max(final)<=.5 and peak<=12 and saturated==0
 return {'schema_version':1,'status':'ANALYSIS_ONLY','procurement_allowed':False,'flight_readiness':'UNDETERMINED','scope':'SMALL_ANGLE_ATTITUDE_ONLY','parameter_evidence':'PLANNING_ASSUMPTION','parameters':asdict(p),'rotor_order':['R1','R2','R3','R4','R5','R6'],'rotation':['CCW','CW','CCW','CW','CCW','CW'],'allocation_matrix':a,'criteria':{'final_abs_angle_deg_max':.5,'peak_abs_angle_deg_max':12,'saturated_channel_steps_max':0},'metrics':metrics,'scenario_result':'PASS' if passed else 'FAIL','samples':samples,'limitations':['Small-angle decoupled attitude dynamics','Fixed total thrust; no translation or altitude coupling','No motor lag, aerodynamics, estimator, noise, battery, or structure','Planning parameters are not hardware selections']}

def main():
 q=argparse.ArgumentParser(description=__doc__);q.add_argument('--output',type=Path,required=True);args=q.parse_args()
 try:r=simulate()
 except ValueError as e:q.error(str(e))
 args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(r,indent=2,allow_nan=False)+'\n');print(f"Attitude scenario: {r['scenario_result']}; flight: UNDETERMINED");return 0 if r['scenario_result']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
