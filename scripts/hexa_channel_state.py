#!/usr/bin/env python3
"""Offline six-channel validator; never drives hardware."""
import argparse,json,math
from dataclasses import dataclass,field
from pathlib import Path
ZERO=(0.0,)*6
def num(v):
 if isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v): raise ValueError
 return float(v)
@dataclass
class State:
 timeout:float=.25; state:str='IDLE'; command:tuple=ZERO; sequence:int=-1
 updated:float|None=None; latch:str|None=None; events:list=field(default_factory=list)
 def log(self,p,result,reason=None,requested=ZERO):
  e={'sequence':p.get('sequence'),'sim_time_s':p.get('sim_time_s'),'mode':p.get('mode'),'requested_command':list(requested),'accepted_command':list(self.command),'state':self.state,'result':result,'rejection_reason':reason};self.events.append(e);return e
 def stop(self,r):self.state,self.command,self.latch='STOPPED',ZERO,r
 def apply(self,p,now):
  now=num(now);r=None;q=ZERO;n,m,t,c=p.get('sequence'),p.get('mode'),p.get('sim_time_s'),p.get('motor_command')
  if p.get('schema_version')!=1:r='unsupported_schema'
  elif type(n)is not int or n<0:r='invalid_sequence'
  elif m not in {'IDLE','CHANNEL_TEST','STOP'}:r='invalid_mode'
  else:
   try:t=num(t)
   except ValueError:r='invalid_time'
  if r is None:
   if not isinstance(c,(list,tuple)) or len(c)!=6:r='invalid_command_length'
   else:
    try:q=tuple(num(x) for x in c)
    except ValueError:r='non_finite_command'
  if r is None and any(x<0 or x>1 for x in q):r='command_out_of_range'
  if r is None and n<=self.sequence:r='non_monotonic_sequence'
  if r is None and now-t>self.timeout:r='expired_command'
  if r is None and t>now:r='future_command'
  if r is None and m=='IDLE' and any(q):r='idle_requires_zero'
  if r is None and m=='CHANNEL_TEST' and sum(x>0 for x in q)!=1:r='channel_test_requires_one_nonzero'
  if m=='STOP' and r is None:self.sequence=n;self.stop('explicit_stop');return self.log(p,'STOPPED','explicit_stop',q)
  if self.latch:return self.log(p,'REJECTED','stop_latched',q)
  if r:self.stop(r);return self.log(p,'REJECTED',r,q)
  self.sequence,self.updated,self.state,self.command=n,now,m,q;return self.log(p,'ACCEPTED',requested=q)
 def tick(self,now):
  now=num(now)
  if self.latch is None and self.updated is not None and now-self.updated>self.timeout:self.stop('link_timeout');return self.log({'sim_time_s':now,'mode':'TICK'},'STOPPED','link_timeout')
 def reset(self,now):
  old=self.latch;self.state,self.command,self.updated,self.latch='IDLE',ZERO,None,None;return self.log({'sim_time_s':num(now),'mode':'RESET'},'RESET',old)
 def report(self):return {'schema_version':1,'status':'ANALYSIS_ONLY','procurement_allowed':False,'hardware_output':False,'flight_readiness':'UNDETERMINED','final_state':self.state,'final_command':list(self.command),'events':self.events,'limitations':['simulated dimensionless commands','not an airborne failsafe','no hardware connected']}
def demo():
 s=State()
 def send(n,t,m,c):s.apply({'schema_version':1,'sequence':n,'sim_time_s':t,'mode':m,'motor_command':c},t)
 send(0,0,'IDLE',[0]*6);send(1,.1,'CHANNEL_TEST',[0,0,.35,0,0,0]);send(2,.2,'STOP',[0]*6);send(3,.21,'CHANNEL_TEST',[.2,0,0,0,0,0]);s.reset(.3);return s.report()
def main():
 p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(demo(),indent=2,allow_nan=False)+'\n');print('Offline channel demo: PASS; flight: UNDETERMINED')
if __name__=='__main__':main()
