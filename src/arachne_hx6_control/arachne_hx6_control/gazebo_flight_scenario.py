"""Gazebo takeoff-hover-land scenario for the isolated flight hex."""
import argparse,json,math,time
from pathlib import Path
import rclpy
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from rclpy.node import Node
from std_msgs.msg import Bool
def command_for(t):
 if t<4:return .35,'TAKEOFF'
 if t<7:return 0.,'HOVER'
 if t<12:return -.25,'LAND'
 return 0.,'DISARMED'
def analyze(samples):
 if not samples:return {'scenario_result':'FAIL','reason':'no_odometry'}
 z=[s['z_m'] for s in samples];h=[s['z_m'] for s in samples if s['phase']=='HOVER'];xy=max(math.hypot(s['x_m'],s['y_m']) for s in samples)
 m={'sample_count':len(samples),'initial_altitude_m':z[0],'max_altitude_m':max(z),'final_altitude_m':z[-1],'hover_span_m':max(h)-min(h) if h else None,'max_horizontal_displacement_m':xy}
 ok=m['sample_count']>=20 and m['max_altitude_m']>=.6 and m['final_altitude_m']<=.2 and m['hover_span_m'] is not None and m['hover_span_m']<=.15 and xy<=.1
 return {'schema_version':1,'status':'ANALYSIS_ONLY','procurement_allowed':False,'flight_readiness':'UNDETERMINED','scope':'GAZEBO_PLANNING_MODEL','parameter_evidence':'PLANNING_ASSUMPTION','criteria':{'minimum_max_altitude_m':.6,'maximum_final_altitude_m':.2,'maximum_hover_span_m':.15,'maximum_horizontal_displacement_m':.1},'metrics':m,'scenario_result':'PASS' if ok else 'FAIL','limitations':['Gazebo parameters are not measured hardware data','Velocity plugin is not a selected flight controller','Simulation pass does not prove physical flight readiness']}
class Scenario(Node):
 def __init__(self,out):
  super().__init__('gazebo_flight_scenario');self.out=out;self.start=time.monotonic();self.samples=[];self.done=False
  self.cmd=self.create_publisher(Twist,'/arachne_hx6/command/twist',10);self.enable=self.create_publisher(Bool,'/arachne_hx6/enable',10)
  self.create_subscription(Odometry,'/model/arachne_flight_hex/odometry',self.odom,10);self.create_timer(.05,self.step)
 def odom(self,msg):
  t=time.monotonic()-self.start;_,phase=command_for(t);p=msg.pose.pose.position;self.samples.append({'elapsed_s':t,'phase':phase,'x_m':p.x,'y_m':p.y,'z_m':p.z})
 def step(self):
  t=time.monotonic()-self.start;speed,phase=command_for(t);e=Bool();e.data=phase!='DISARMED';self.enable.publish(e);m=Twist();m.linear.z=speed;self.cmd.publish(m)
  if t>=13 and not self.done:
   self.done=True;r=analyze(self.samples);self.out.parent.mkdir(parents=True,exist_ok=True);self.out.write_text(json.dumps(r,indent=2,allow_nan=False)+'\n');print(f"Gazebo flight scenario: {r['scenario_result']}; flight: UNDETERMINED",flush=True);rclpy.shutdown()
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);a=p.parse_args();rclpy.init();n=Scenario(a.output)
 try:rclpy.spin(n)
 finally:n.destroy_node()
 r=json.loads(a.output.read_text()) if a.output.exists() else {'scenario_result':'FAIL'};return 0 if r['scenario_result']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
