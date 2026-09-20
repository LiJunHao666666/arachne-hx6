from arachne_hx6_control.gazebo_flight_scenario import analyze,command_for
def test_phase_schedule():
 assert command_for(0)==(.35,'TAKEOFF');assert command_for(4)==(0.,'HOVER');assert command_for(7)==(-.25,'LAND');assert command_for(12)==(0.,'DISARMED')
def test_accepts_complete_flight_shape():
 s=[{'phase':'TAKEOFF','x_m':0,'y_m':0,'z_m':.02} for _ in range(10)]+[{'phase':'HOVER','x_m':.01,'y_m':0,'z_m':z} for z in [.68,.70,.72]*5]+[{'phase':'LAND','x_m':0,'y_m':0,'z_m':.05} for _ in range(10)]
 r=analyze(s);assert r['scenario_result']=='PASS';assert r['procurement_allowed'] is False
def test_rejects_missing_or_unsafe_evidence():
 assert analyze([])['scenario_result']=='FAIL';bad=[{'phase':'HOVER','x_m':.2,'y_m':0,'z_m':.1} for _ in range(30)];assert analyze(bad)['scenario_result']=='FAIL'
