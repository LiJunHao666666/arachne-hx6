"""Shared provenance contract for planning-only Gazebo flight evidence."""

RESULT_SCHEMA = 'arachne.flight-sim-result/v1'
MODEL = {'id': 'arachne-flight-hex', 'version': '1'}
CONTROLLER = {'id': 'gz-multicopter-velocity-control', 'version': '1'}
COMMAND_GUARD = {
    'id': 'arachne-command-loss-landing-guard',
    'version': '1',
}


def result_header(scenario_id, scenario_version, *, guarded=False):
    """Return the mandatory provenance and evidence-boundary fields."""
    components = {
        'model': dict(MODEL),
        'controller': dict(CONTROLLER),
    }
    if guarded:
        components['command_guard'] = dict(COMMAND_GUARD)
    return {
        'schema': RESULT_SCHEMA,
        'schema_version': 1,
        'scenario': {'id': scenario_id, 'version': scenario_version},
        'components': components,
        'status': 'ANALYSIS_ONLY',
        'procurement_allowed': False,
        'flight_readiness': 'UNDETERMINED',
        'scope': 'GAZEBO_PLANNING_MODEL',
        'parameter_evidence': 'PLANNING_ASSUMPTION',
    }
