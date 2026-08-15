"""G1.5 ANALYSIS_ONLY propulsion feasibility tests. No GUI."""

from __future__ import annotations

from dataclasses import replace
import csv
import json
import math
from pathlib import Path

import pytest

from arachne_hx6_analysis.cli import main
from arachne_hx6_analysis.model import (
    GATE_CONDITIONAL_CANDIDATE,
    GATE_REJECTED_FOR_CURRENT_BASELINE,
    INCH_TO_METRE,
    N1_STATIC_FLAG,
    REQUIRED_UNCERTAINTY_CASES,
    ROOT_METHOD_BISECTION,
    STATUS_ANALYSIS_ONLY,
    STATUS_CONDITIONAL_ENERGY_CLOSURE,
    STATUS_ENERGY_MASS_CLOSURE_INFEASIBLE,
    STATUS_NOT_FOR_PROCUREMENT,
    STATUS_OVERALL_UNDETERMINED,
    ConvergenceError,
    InvalidInputError,
    adjacent_motor_center_distance_m,
    battery_bus_current_a,
    critical_total_mass_kg,
    electrical_hover_power_w,
    energy_mass_residual_kg,
    hover_thrust_n,
    hover_thrust_per_motor_n,
    ideal_induced_power_w,
    inches_to_metres,
    max_thrust_per_motor_n,
    maximum_non_battery_mass_for_closure_kg,
    min_motor_center_radius_m,
    n1_burden_increase_fraction,
    required_battery_mass_kg,
    rotor_disk_area_m2,
    rotor_envelope_diameter_m,
    total_rotor_disk_area_m2,
)
from arachne_hx6_analysis.report import (
    CSV_NAME,
    JSON_NAME,
    MARKDOWN_NAME,
    MD_NULL,
    write_reports,
)
from arachne_hx6_analysis.solver import (
    apply_uncertainty_case,
    energy_mass_coefficients,
    evaluate_hover_at_mass,
    load_analysis_config,
    solve_all,
    solve_all_uncertainty_cases,
    solve_battery_feedback,
)

_PACKAGE_ROOT = Path(__file__).resolve().parent.parent
_CONFIG_PATH = _PACKAGE_ROOT / 'config' / 'propulsion_scenarios.yaml'

_CLOSED_MASS_FIELDS = (
    'battery_mass_kg',
    'total_mass_kg',
    'hover_thrust_n',
    'hover_thrust_kgf',
    'hover_thrust_per_motor_n',
    'hover_thrust_per_motor_kgf',
    'max_thrust_per_motor_n',
    'max_thrust_per_motor_kgf',
    'disk_loading_n_m2',
    'disk_loading_kg_m2',
    'ideal_induced_power_w',
    'ideal_induced_power_per_motor_w',
    'electrical_hover_power_w',
    'battery_bus_current_a',
    'n1_hover_thrust_per_remaining_motor_n',
    'n1_hover_thrust_per_remaining_motor_kgf',
    'n1_max_thrust_per_remaining_motor_n',
    'n1_max_thrust_per_remaining_motor_kgf',
    'residual_kg',
    'battery_mass_fraction',
)


@pytest.fixture(scope='module')
def config():
    return load_analysis_config(_CONFIG_PATH)


@pytest.fixture(scope='module')
def nominal_rows(config):
    return solve_all(config, uncertainty_case='nominal')


def test_inches_to_metres():
    assert inches_to_metres(1.0) == pytest.approx(INCH_TO_METRE)
    assert inches_to_metres(4.7) == pytest.approx(4.7 * INCH_TO_METRE)
    assert inches_to_metres(12.0) == pytest.approx(0.3048)
    assert inches_to_metres(15.0) == pytest.approx(0.381)


def test_rotor_disk_area_formula():
    diameter_m = 0.20
    expected = math.pi * (diameter_m / 2.0) ** 2
    assert rotor_disk_area_m2(diameter_m) == pytest.approx(expected)
    assert total_rotor_disk_area_m2(diameter_m, 6) == pytest.approx(6.0 * expected)


def test_thrust_allocation():
    mass_kg = 6.0
    gravity = 10.0
    assert hover_thrust_n(mass_kg, gravity) == pytest.approx(60.0)
    assert hover_thrust_per_motor_n(mass_kg, gravity, 6) == pytest.approx(10.0)


def test_thrust_to_weight_max_thrust():
    assert max_thrust_per_motor_n(6.0, 10.0, 6, 1.8) == pytest.approx(18.0)


def test_ideal_induced_power_formula():
    thrust_n = 12.0
    area_m2 = 0.05
    rho = 1.225
    expected = (thrust_n ** 1.5) / math.sqrt(2.0 * rho * area_m2)
    assert ideal_induced_power_w(thrust_n, area_m2, rho) == pytest.approx(expected)


def test_larger_diameter_lowers_ideal_power_at_same_mass(config):
    small = evaluate_hover_at_mass(config, 10.0, 4.7)
    large = evaluate_hover_at_mass(config, 10.0, 15.0)
    assert large['ideal_induced_power_w'] < small['ideal_induced_power_w']
    assert large['area_total_m2'] > small['area_total_m2']


def test_higher_mass_raises_power_at_same_diameter(config):
    light = evaluate_hover_at_mass(config, 8.0, 12.0)
    heavy = evaluate_hover_at_mass(config, 16.0, 12.0)
    assert heavy['ideal_induced_power_w'] > light['ideal_induced_power_w']
    assert heavy['electrical_hover_power_w'] > light['electrical_hover_power_w']


def test_battery_bus_current_is_total_dc_input(config):
    hover = evaluate_hover_at_mass(config, 10.0, 12.0)
    assert hover['battery_bus_current_a'] == pytest.approx(
        battery_bus_current_a(
            hover['electrical_hover_power_w'], config.bus_voltage_v
        )
    )
    assert 'hover_current_a' not in hover


def test_analytic_existence_matches_f_min_sign(config):
    for diameter_inch in config.propellers_inch:
        c, k = energy_mass_coefficients(config, diameter_inch)
        m_crit = critical_total_mass_kg(k)
        m_nb_max = maximum_non_battery_mass_for_closure_kg(c, k)
        assert m_crit == pytest.approx((2.0 / (3.0 * k)) ** 2)
        for scenario in config.mass_scenarios:
            f_min = energy_mass_residual_kg(
                m_crit, scenario.non_battery_mass_kg, c, k
            )
            exists = f_min <= 0.0
            assert exists == (scenario.non_battery_mass_kg <= m_nb_max + 1.0e-12)


def test_47_inch_all_masses_are_analytically_infeasible(config, nominal_rows):
    rows_47 = [
        row for row in nominal_rows if abs(row.diameter_inch - 4.7) < 1.0e-9
    ]
    assert len(rows_47) == 3
    for row in rows_47:
        c, k = energy_mass_coefficients(config, row.diameter_inch)
        f_min = energy_mass_residual_kg(
            row.critical_total_mass_kg,
            row.non_battery_mass_kg,
            c,
            k,
        )
        assert f_min > 0.0
        assert row.closure_margin_kg < 0.0
        assert row.energy_mass_closure is False
        assert (
            row.energy_mass_closure_status
            == STATUS_ENERGY_MASS_CLOSURE_INFEASIBLE
        )
        assert STATUS_ENERGY_MASS_CLOSURE_INFEASIBLE in row.risk_flags
        assert row.root_method == 'none'
        assert row.current_geometry_fit is True
        assert row.battery_mass_kg is None
        assert row.total_mass_kg is None


def test_12_and_15_inch_have_smaller_physical_roots(config, nominal_rows):
    closed = [
        row for row in nominal_rows
        if abs(row.diameter_inch - 12.0) < 1.0e-9
        or abs(row.diameter_inch - 15.0) < 1.0e-9
    ]
    assert len(closed) == 6
    for row in closed:
        assert row.energy_mass_closure is True
        assert (
            row.energy_mass_closure_status
            == STATUS_CONDITIONAL_ENERGY_CLOSURE
        )
        assert row.root_method == ROOT_METHOD_BISECTION
        assert row.total_mass_kg is not None
        assert row.battery_mass_kg is not None
        assert row.total_mass_kg == pytest.approx(
            row.non_battery_mass_kg + row.battery_mass_kg
        )
        assert row.non_battery_mass_kg <= row.total_mass_kg
        assert row.total_mass_kg <= row.critical_total_mass_kg
        c, k = energy_mass_coefficients(config, row.diameter_inch)
        residual = energy_mass_residual_kg(
            row.total_mass_kg, row.non_battery_mass_kg, c, k
        )
        assert abs(residual) <= config.mass_tolerance_kg
        assert abs(row.residual_kg) <= config.mass_tolerance_kg
        assert row.current_geometry_fit is False


def test_bisection_residual_meets_tolerance(config, nominal_rows):
    for row in nominal_rows:
        if not row.energy_mass_closure:
            continue
        assert abs(row.residual_kg) <= config.mass_tolerance_kg
        assert row.root_iterations >= 0
        assert row.root_method == ROOT_METHOD_BISECTION


def test_infeasible_official_fields_are_null(nominal_rows):
    for row in nominal_rows:
        if row.energy_mass_closure:
            continue
        for field_name in _CLOSED_MASS_FIELDS:
            assert getattr(row, field_name) is None, field_name
        assert row.diagnostic_first_iteration_battery_mass_kg > 0.0
        assert row.diagnostic_non_battery_mass_power_w > 0.0


def test_diagnostic_fields_are_isolated_from_official_results(nominal_rows):
    for row in nominal_rows:
        assert row.diagnostic_first_iteration_battery_mass_kg > 0.0
        assert row.diagnostic_non_battery_mass_power_w > 0.0
        if not row.energy_mass_closure:
            assert row.battery_mass_kg is None
            assert row.total_mass_kg is None
            assert row.electrical_hover_power_w is None
            assert row.hover_thrust_n is None
        else:
            assert row.battery_mass_kg is not None
            assert row.diagnostic_first_iteration_battery_mass_kg != pytest.approx(
                row.battery_mass_kg
            )


def test_current_field_renamed_to_battery_bus_current(nominal_rows):
    payload = [row.as_dict() for row in nominal_rows]
    for item in payload:
        assert 'battery_bus_current_a' in item
        assert 'hover_current_a' not in item
        assert 'current_a' not in item
        assert 'nominal bus' in item['battery_bus_current_note']


def test_n1_hexarotor_burden_is_20_percent(nominal_rows):
    assert n1_burden_increase_fraction(6) == pytest.approx(0.20)
    for row in nominal_rows:
        assert row.n1_burden_increase_fraction == pytest.approx(0.20)
        assert row.n1_interpretation == N1_STATIC_FLAG
        assert N1_STATIC_FLAG in row.risk_flags
        if row.energy_mass_closure:
            assert row.n1_hover_thrust_per_remaining_motor_n == pytest.approx(
                row.hover_thrust_per_motor_n * 1.20
            )
            assert row.n1_max_thrust_per_remaining_motor_n == pytest.approx(
                row.max_thrust_per_motor_n * 6.0 / 5.0
            )


def test_combined_gate_rejects_all_current_diameters(nominal_rows):
    by_d = {}
    for row in nominal_rows:
        by_d.setdefault(row.diameter_inch, []).append(row)
    for row in by_d[4.7]:
        assert row.current_geometry_fit is True
        assert (
            row.energy_mass_closure_status
            == STATUS_ENERGY_MASS_CLOSURE_INFEASIBLE
        )
        assert (
            row.combined_current_baseline_gate
            == GATE_REJECTED_FOR_CURRENT_BASELINE
        )
    for diameter in (12.0, 15.0):
        for row in by_d[diameter]:
            assert row.current_geometry_fit is False
            assert (
                row.energy_mass_closure_status
                == STATUS_CONDITIONAL_ENERGY_CLOSURE
            )
            assert (
                row.combined_current_baseline_gate
                == GATE_REJECTED_FOR_CURRENT_BASELINE
            )
    assert all(
        row.combined_current_baseline_gate != GATE_CONDITIONAL_CANDIDATE
        for row in nominal_rows
    )
    assert all(
        row.overall_propulsion_feasibility == STATUS_OVERALL_UNDETERMINED
        for row in nominal_rows
    )


def test_uncertainty_cases_are_complete(config):
    names = tuple(case.name for case in config.uncertainty_cases)
    assert names == REQUIRED_UNCERTAINTY_CASES
    fields = (
        'air_density_kg_m3',
        'figure_of_merit',
        'motor_esc_efficiency',
        'pack_specific_energy_wh_kg',
        'usable_fraction',
        'avionics_power_w',
    )
    by_name = {case.name: case for case in config.uncertainty_cases}
    for name in REQUIRED_UNCERTAINTY_CASES:
        case = by_name[name]
        for field_name in fields:
            value = getattr(case, field_name)
            assert isinstance(value, float)
            assert math.isfinite(value)
        assert case.description
    cons = by_name['conservative']
    nom = by_name['nominal']
    opt = by_name['optimistic']
    assert cons.figure_of_merit < nom.figure_of_merit < opt.figure_of_merit
    assert (
        cons.pack_specific_energy_wh_kg
        < nom.pack_specific_energy_wh_kg
        < opt.pack_specific_energy_wh_kg
    )
    assert cons.avionics_power_w > nom.avionics_power_w > opt.avionics_power_w
    assert nom.air_density_kg_m3 == pytest.approx(config.air_density_kg_m3)
    assert nom.figure_of_merit == pytest.approx(config.figure_of_merit)
    assert nom.motor_esc_efficiency == pytest.approx(config.motor_esc_efficiency)
    assert nom.pack_specific_energy_wh_kg == pytest.approx(
        config.pack_specific_energy_wh_kg
    )
    assert nom.usable_fraction == pytest.approx(config.usable_fraction)
    assert nom.avionics_power_w == pytest.approx(config.avionics_power_w)


def test_conservative_nominal_optimistic_outputs_are_complete(config):
    by_case = solve_all_uncertainty_cases(config)
    assert set(by_case) == set(REQUIRED_UNCERTAINTY_CASES)
    for name in REQUIRED_UNCERTAINTY_CASES:
        rows = by_case[name]
        assert len(rows) == 9
        for row in rows:
            assert row.uncertainty_case == name
            assert row.status == STATUS_ANALYSIS_ONLY
            assert STATUS_NOT_FOR_PROCUREMENT in row.risk_flags
            assert row.overall_propulsion_feasibility == STATUS_OVERALL_UNDETERMINED
            assert row.critical_total_mass_kg > 0.0
            assert row.diagnostic_first_iteration_battery_mass_kg > 0.0
            assert row.energy_mass_closure_status in {
                STATUS_CONDITIONAL_ENERGY_CLOSURE,
                STATUS_ENERGY_MASS_CLOSURE_INFEASIBLE,
            }
            assert row.combined_current_baseline_gate in {
                GATE_CONDITIONAL_CANDIDATE,
                GATE_REJECTED_FOR_CURRENT_BASELINE,
            }


def test_reports_contain_analysis_only_banners(config, nominal_rows, tmp_path):
    by_case = solve_all_uncertainty_cases(config)
    paths = write_reports(
        config,
        nominal_rows,
        tmp_path,
        results_by_uncertainty=by_case,
    )
    json_text = paths['json'].read_text(encoding='utf-8')
    csv_text = paths['csv'].read_text(encoding='utf-8')
    md_text = paths['markdown'].read_text(encoding='utf-8')
    for text in (json_text, csv_text, md_text):
        assert STATUS_ANALYSIS_ONLY in text
        assert STATUS_NOT_FOR_PROCUREMENT in text
    payload = json.loads(json_text)
    assert payload['overall_propulsion_feasibility'] == STATUS_OVERALL_UNDETERMINED
    assert payload['any_conditional_candidate'] is False
    assert set(payload['results_by_uncertainty']) == set(REQUIRED_UNCERTAINTY_CASES)


def test_invalid_inputs_are_rejected(config):
    with pytest.raises(InvalidInputError):
        inches_to_metres(0.0)
    with pytest.raises(InvalidInputError):
        inches_to_metres(-1.0)
    with pytest.raises(InvalidInputError):
        rotor_disk_area_m2(-0.2)
    with pytest.raises(InvalidInputError):
        hover_thrust_n(0.0, 9.81)
    with pytest.raises(InvalidInputError):
        electrical_hover_power_w(100.0, 0.0, 0.8, 0.0)
    with pytest.raises(InvalidInputError):
        electrical_hover_power_w(100.0, 1.1, 0.8, 0.0)
    with pytest.raises(InvalidInputError):
        electrical_hover_power_w(100.0, 0.7, -0.1, 0.0)
    with pytest.raises(InvalidInputError):
        required_battery_mass_kg(100.0, 60.0, 180.0, 0.0)
    with pytest.raises(InvalidInputError):
        required_battery_mass_kg(100.0, 60.0, 180.0, 1.2)
    with pytest.raises(InvalidInputError):
        replace(config, figure_of_merit=0.0).validate()
    with pytest.raises(InvalidInputError):
        replace(config, motor_esc_efficiency=1.01).validate()
    with pytest.raises(InvalidInputError):
        replace(config, rotor_count=1).validate()
    with pytest.raises(InvalidInputError):
        replace(config, air_density_kg_m3=-1.0).validate()
    with pytest.raises(InvalidInputError):
        load_analysis_config(Path('/tmp/does_not_exist_arachne_g15.yaml'))


def test_analytic_infeasibility_is_not_a_fixed_point_failure(config):
    stubborn = replace(config, max_iterations=1, mass_tolerance_kg=1.0e-12)
    scenario = config.mass_scenarios[0]
    row = solve_battery_feedback(stubborn, scenario, 4.7)
    assert row.energy_mass_closure is False
    assert row.energy_mass_closure_status == STATUS_ENERGY_MASS_CLOSURE_INFEASIBLE
    assert row.battery_mass_kg is None
    with pytest.raises(ConvergenceError):
        solve_battery_feedback(stubborn, scenario, 12.0)


def test_hexarotor_geometry_spacing():
    radius_m = 0.30
    rotor_count = 6
    adjacent = adjacent_motor_center_distance_m(radius_m, rotor_count)
    assert adjacent == pytest.approx(radius_m)
    diameter_m = 0.12
    tip_gap = 0.02
    min_r = min_motor_center_radius_m(diameter_m, tip_gap, rotor_count)
    assert min_r == pytest.approx(diameter_m + tip_gap)
    envelope = rotor_envelope_diameter_m(radius_m, diameter_m)
    assert envelope == pytest.approx(2.0 * radius_m + diameter_m)


def test_report_null_semantics_and_emdash(config, nominal_rows, tmp_path):
    diameters = sorted({row.diameter_inch for row in nominal_rows})
    scenarios = {row.scenario_name for row in nominal_rows}
    assert diameters == pytest.approx([4.7, 12.0, 15.0])
    assert scenarios == {'g1_placeholder', 'planned', 'growth'}
    assert len(nominal_rows) == 9
    for row in nominal_rows:
        assert row.status == STATUS_ANALYSIS_ONLY
        assert STATUS_NOT_FOR_PROCUREMENT in row.risk_flags
        assert row.procurement_allowed is False
        assert row.area_one_m2 > 0.0
        assert row.min_motor_center_radius_m > 0.0
    paths = write_reports(config, nominal_rows, tmp_path)
    json_text = paths['json'].read_text(encoding='utf-8')
    csv_text = paths['csv'].read_text(encoding='utf-8')
    md_text = paths['markdown'].read_text(encoding='utf-8')
    payload = json.loads(json_text)
    assert payload['status'] == STATUS_ANALYSIS_ONLY
    assert payload['not_for_procurement'] == STATUS_NOT_FOR_PROCUREMENT
    assert payload['procurement_allowed'] is False
    assert len(payload['results']) == 9
    infeasible = [
        item for item in payload['results']
        if abs(item['diameter_inch'] - 4.7) < 1.0e-9
    ]
    assert infeasible
    for item in infeasible:
        assert item['battery_mass_kg'] is None
        assert item['total_mass_kg'] is None
        assert item['battery_bus_current_a'] is None
        assert item['hover_thrust_n'] is None
        assert item['diagnostic_first_iteration_battery_mass_kg'] is not None
        assert item['diagnostic_non_battery_mass_power_w'] is not None
    assert MD_NULL in md_text
    assert '*INFEASIBLE*' not in md_text
    csv_rows = list(csv.DictReader(csv_text.splitlines()))
    csv_47 = [
        item for item in csv_rows
        if abs(float(item['diameter_inch']) - 4.7) < 1.0e-9
        and item['uncertainty_case'] in ('', 'nominal')
    ]
    assert csv_47
    for item in csv_47:
        assert item['battery_mass_kg'] == ''
        assert item['total_mass_kg'] == ''
        assert item['battery_bus_current_a'] == ''
        assert item['diagnostic_first_iteration_battery_mass_kg'] != ''
    assert 'battery_bus_current_a' in csv_text
    assert 'hover_current_a' not in csv_text.splitlines()[0]
    assert STATUS_CONDITIONAL_ENERGY_CLOSURE in md_text
    assert '| closed |' not in md_text
    assert N1_STATIC_FLAG in md_text
    assert 'real motor mass' in md_text
    for name in ('conservative', 'nominal', 'optimistic'):
        assert name in md_text
    assert '4.70' in md_text or '4.7' in md_text
    assert '12.00' in md_text or '12.0' in md_text
    assert '15.00' in md_text or '15.0' in md_text


def test_cli_writes_three_artifacts(tmp_path):
    output_dir = tmp_path / 'cli_out'
    rc = main(['--config', str(_CONFIG_PATH), '--output-dir', str(output_dir)])
    assert rc == 0
    assert (output_dir / JSON_NAME).is_file()
    assert (output_dir / CSV_NAME).is_file()
    assert (output_dir / MARKDOWN_NAME).is_file()
    markdown = (output_dir / MARKDOWN_NAME).read_text(encoding='utf-8')
    assert markdown.splitlines()[2] == f'**{STATUS_ANALYSIS_ONLY}**'
    assert markdown.splitlines()[3] == f'**{STATUS_NOT_FOR_PROCUREMENT}**'
    payload = json.loads((output_dir / JSON_NAME).read_text(encoding='utf-8'))
    assert set(payload['results_by_uncertainty']) == set(REQUIRED_UNCERTAINTY_CASES)


def test_apply_uncertainty_changes_overlay_fields(config):
    cons = next(
        case for case in config.uncertainty_cases if case.name == 'conservative'
    )
    overlaid = apply_uncertainty_case(config, cons)
    assert overlaid.figure_of_merit == cons.figure_of_merit
    assert overlaid.air_density_kg_m3 == cons.air_density_kg_m3
    assert overlaid.avionics_power_w == cons.avionics_power_w
    assert overlaid.rotor_count == config.rotor_count
    assert overlaid.current_motor_center_radius_m == (
        config.current_motor_center_radius_m
    )
