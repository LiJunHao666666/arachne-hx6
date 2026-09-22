#!/usr/bin/env python3
"""Generate the local ANALYSIS_ONLY Gazebo hexarotor SDF."""
from pathlib import Path
import math

HEADER='''<?xml version="1.0"?>
<sdf version="1.10">
  <model name="arachne_flight_hex">
    <pose>0 0 0.18 0 0 0</pose>
    <link name="base_link">
      <inertial><mass>0.62</mass><inertia><ixx>0.004</ixx><iyy>0.004</iyy><izz>0.007</izz></inertia></inertial>
      <collision name="body_collision"><geometry><cylinder><radius>0.035</radius><length>0.04</length></cylinder></geometry></collision>
      <visual name="body_visual"><geometry><cylinder><radius>0.035</radius><length>0.04</length></cylinder></geometry><material><diffuse>0.12 0.22 0.35 1</diffuse></material></visual>
      <!-- Visual-only nose: body +X forward, +Y left, +Z up. -->
      <visual name="nose_positive_x"><pose>0.04 0 0.027 0 0 0</pose><geometry><box><size>0.05 0.012 0.008</size></box></geometry><material><diffuse>1 0.25 0.02 1</diffuse><ambient>1 0.25 0.02 1</ambient></material></visual>
    </link>
'''
FOOTER='''    <plugin filename="gz-sim-multicopter-control-system" name="gz::sim::systems::MulticopterVelocityControl">
      <robotNamespace>arachne_hx6</robotNamespace><commandSubTopic>command/twist</commandSubTopic><enableSubTopic>enable</enableSubTopic><comLinkName>base_link</comLinkName>
      <velocityGain>6 6 10</velocityGain><attitudeGain>4 4 2</attitudeGain><angularRateGain>0.7 0.7 0.7</angularRateGain>
      <maximumLinearAcceleration>1 1 2</maximumLinearAcceleration><maximumLinearVelocity>2 2 2</maximumLinearVelocity><maximumAngularVelocity>2 2 2</maximumAngularVelocity>
      <linearVelocityNoiseMean>0 0 0</linearVelocityNoiseMean><linearVelocityNoiseStdDev>0 0 0</linearVelocityNoiseStdDev>
      <angularVelocityNoiseMean>0 0 0</angularVelocityNoiseMean><angularVelocityNoiseStdDev>0 0 0</angularVelocityNoiseStdDev>
      <rotorConfiguration>
{rotor_config}
      </rotorConfiguration>
    </plugin>
    <plugin filename="gz-sim-odometry-publisher-system" name="gz::sim::systems::OdometryPublisher"><dimensions>3</dimensions></plugin>
  </model>
</sdf>
'''
def generate():
 parts=[HEADER];config=[]
 for i in range(6):
  angle=math.radians(30+60*i);x=.12*math.cos(angle);y=.12*math.sin(angle);direction='ccw' if i%2==0 else 'cw';sign=1 if i%2==0 else -1
  parts.append(f'''    <link name="rotor_{i}"><pose relative_to="base_link">{x:.9f} {y:.9f} 0.025 0 0 0</pose><inertial><mass>0.005</mass><inertia><ixx>0.00001</ixx><iyy>0.00001</iyy><izz>0.00002</izz></inertia></inertial><visual name="visual"><geometry><cylinder><radius>0.045</radius><length>0.002</length></cylinder></geometry><material><diffuse>0.25 0.65 0.95 0.35</diffuse></material></visual></link>
    <joint name="rotor_{i}_joint" type="revolute"><parent>base_link</parent><child>rotor_{i}</child><axis><xyz>0 0 1</xyz></axis></joint>
    <plugin filename="gz-sim-multicopter-motor-model-system" name="gz::sim::systems::MulticopterMotorModel"><robotNamespace>arachne_hx6</robotNamespace><jointName>rotor_{i}_joint</jointName><linkName>rotor_{i}</linkName><turningDirection>{direction}</turningDirection><timeConstantUp>0.0182</timeConstantUp><timeConstantDown>0.0182</timeConstantDown><maxRotVelocity>1000</maxRotVelocity><motorConstant>1.269e-05</motorConstant><momentConstant>0.016754</momentConstant><commandSubTopic>command/motor_speed</commandSubTopic><actuator_number>{i}</actuator_number><rotorDragCoefficient>0</rotorDragCoefficient><rollingMomentCoefficient>0</rollingMomentCoefficient><motorSpeedPubTopic>motor_speed/{i}</motorSpeedPubTopic><rotorVelocitySlowdownSim>2</rotorVelocitySlowdownSim><motorType>velocity</motorType></plugin>
''')
  config.append(f'''        <rotor><jointName>rotor_{i}_joint</jointName><forceConstant>1.269e-05</forceConstant><momentConstant>1.6754e-2</momentConstant><direction>{sign}</direction></rotor>''')
 return ''.join(parts)+FOOTER.format(rotor_config='\n'.join(config))
def generate_world():
 model=generate();model=model[model.index('  <model'):model.rindex('</sdf>')]
 return '''<?xml version="1.0"?>
<sdf version="1.10"><world name="arachne_flight">
<physics name="2ms" type="ignored"><max_step_size>0.002</max_step_size><real_time_factor>1</real_time_factor></physics>
<plugin filename="gz-sim-physics-system" name="gz::sim::systems::Physics"/>
<plugin filename="gz-sim-scene-broadcaster-system" name="gz::sim::systems::SceneBroadcaster"/>
<plugin filename="gz-sim-user-commands-system" name="gz::sim::systems::UserCommands"/>
<light type="directional" name="sun"><pose>0 0 10 0 0 0</pose><direction>-0.5 0.1 -0.9</direction></light>
<model name="ground"><static>true</static><link name="link"><collision name="collision"><geometry><plane><normal>0 0 1</normal><size>20 20</size></plane></geometry></collision><visual name="visual"><geometry><plane><normal>0 0 1</normal><size>20 20</size></plane></geometry></visual></link></model>
'''+model+'''</world></sdf>
'''

def main():
 root=Path(__file__).resolve().parents[1]
 out=root/'src/arachne_hx6_simulation/models/arachne_flight_hex/model.sdf';out.parent.mkdir(parents=True,exist_ok=True);out.write_text(generate(),encoding='utf-8')
 (root/'src/arachne_hx6_simulation/worlds/flight_hex.sdf').write_text(generate_world(),encoding='utf-8')
if __name__=='__main__':main()
