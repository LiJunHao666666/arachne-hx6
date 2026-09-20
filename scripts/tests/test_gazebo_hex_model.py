"""Validate the generated local Gazebo hexarotor model."""
import importlib.util
from pathlib import Path
import xml.etree.ElementTree as ET
P=Path(__file__).resolve().parents[1]/'generate_gazebo_hex.py';S=importlib.util.spec_from_file_location('gen',P);M=importlib.util.module_from_spec(S);S.loader.exec_module(M)
def test_model_has_six_rotors_and_plugins():
 root=ET.fromstring(M.generate());model=root.find('model')
 assert len([x for x in model.findall('link') if x.get('name','').startswith('rotor_')])==6
 assert len([x for x in model.findall('joint') if x.get('name','').startswith('rotor_')])==6
 motors=[x for x in model.findall('plugin') if 'MotorModel' in x.get('name','')]
 assert len(motors)==6;assert [int(x.findtext('actuator_number')) for x in motors]==list(range(6))
 assert [x.findtext('turningDirection') for x in motors]==['ccw','cw','ccw','cw','ccw','cw']
def test_analysis_parameters_and_controller():
 root=ET.fromstring(M.generate());model=root.find('model');assert float(model.find("link[@name='base_link']/inertial/mass").text)==.62
 control=[x for x in model.findall('plugin') if 'VelocityControl' in x.get('name','')][0]
 assert len(control.findall('rotorConfiguration/rotor'))==6
def test_generated_file_matches_source():
 expected=M.generate();actual=(P.parents[1]/'src/arachne_hx6_simulation/models/arachne_flight_hex/model.sdf').read_text()
 assert actual==expected

def test_generated_world_matches_source_and_is_offline():
 world=M.generate_world()
 assert '../models/' not in world and 'model://' not in world and 'http' not in world
 actual=(P.parents[1]/'src/arachne_hx6_simulation/worlds/flight_hex.sdf').read_text()
 assert actual==world
