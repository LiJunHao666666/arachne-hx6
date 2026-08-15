"""Write ANALYSIS_ONLY JSON, CSV, and Markdown propulsion reports."""

from __future__ import annotations

import csv
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from arachne_hx6_analysis.model import (
    GATE_CONDITIONAL_CANDIDATE,
    MISSING_CLOSED_VEHICLE_MASS_ITEMS,
    N1_STATIC_FLAG,
    REQUIRED_UNCERTAINTY_CASES,
    STATUS_ANALYSIS_ONLY,
    STATUS_NOT_FOR_PROCUREMENT,
    STATUS_OVERALL_UNDETERMINED,
    AnalysisConfig,
)
from arachne_hx6_analysis.solver import PropulsionResult

JSON_NAME = 'propulsion_feasibility.json'
CSV_NAME = 'propulsion_feasibility.csv'
MARKDOWN_NAME = 'propulsion_feasibility.md'
MD_NULL = '—'

EQUATIONS = (
    ('inches_to_metres', 'D_m = D_in * 0.0254', 'm'),
    ('rotor_disk_area', 'A = pi * (D/2)^2', 'm^2'),
    ('total_disk_area', 'A_total = n * A', 'm^2'),
    ('hover_thrust', 'T = m * g', 'N'),
    ('hover_thrust_kgf', 'T_kgf = T / g', 'kgf'),
    ('hover_thrust_per_motor', 'T_motor = T / n', 'N and kgf'),
    (
        'required_thrust_per_motor_at_target_tw',
        'T_req = (T/W) * m * g / n  (planning demand, not motor capability)',
        'N and kgf',
    ),
    ('disk_loading_si', 'DL = T / A_total', 'N/m^2'),
    ('disk_loading_kg', 'DL_kg = m / A_total', 'kg/m^2'),
    (
        'ideal_induced_power',
        'P_ideal = T_motor^(3/2) / sqrt(2 * rho * A); P_total = n * P_ideal',
        'W',
    ),
    (
        'ideal_induced_power_per_motor',
        'P_ideal_motor = P_ideal_total / n  (mechanical reference only)',
        'W',
    ),
    (
        'electrical_hover_power',
        'P_elec = P_ideal_total / (FoM * eta_motor_esc) + P_avionics',
        'W',
    ),
    (
        'battery_bus_current',
        'I_bus = P_elec / V_bus_nominal  (total DC input; not phase current)',
        'A',
    ),
    (
        'battery_mass',
        'm_batt = (P_elec * t_endurance / 3600) / (e_pack * usable_fraction)',
        'kg',
    ),
    (
        'energy_mass_residual',
        'F(m) = m_non_battery + c + k * m^(3/2) - m',
        'kg',
    ),
    (
        'critical_total_mass',
        'm_critical = (2 / (3 * k))^2',
        'kg',
    ),
    (
        'energy_mass_closure_existence',
        'exists iff F(m_critical) <= 0; smaller root by bisection on '
        '[m_non_battery, m_critical]',
        'kg',
    ),
    (
        'adjacent_motor_distance',
        'd_adj = 2 * R * sin(pi / n)',
        'm',
    ),
    (
        'min_motor_center_radius',
        'R_min = (D + tip_gap) / (2 * sin(pi / n))',
        'm',
    ),
    ('rotor_envelope_diameter', 'D_env = 2 * R + D', 'm'),
    (
        'n1_hover_thrust_per_remaining_motor',
        'T_n1 = T / (n - 1); burden_increase = n/(n-1) - 1',
        'N and kgf',
    ),
    (
        'n1_required_thrust_per_remaining_motor_at_target_tw',
        'T_n1_req = (T/W) * m * g / (n-1)  (planning demand, not motor capability)',
        'N and kgf',
    ),
)

UNMODELED = (
    'No blade-element, stall, Mach, or Reynolds-number model.',
    'No motor Kv, current limit, thermal derate, or propeller map.',
    'No translational flight, climb, or hexapod walking power.',
    'No wiring, connector, or BEC losses beyond eta_motor_esc.',
    'No battery Peukert, temperature, or cycle-life effects.',
    'No aero interaction between rotors, legs, pods, or the body.',
    'No structural, vibration, or landing-gear mass growth model.',
    'G1 hex_arm_span is a visual skeleton value; URDF is not modified.',
    'battery_bus_current_a is not a per-motor phase current and omits sag, '
    'line loss, and peak current.',
    'N-1 numbers are static thrust splits only, not control-authority proof.',
    'Energy-mass closure is not whole-vehicle mass closure or a flyable '
    'conclusion.',
    'Results are ANALYSIS_ONLY and must not be used for procurement.',
)

MISSING_MASS_PREAMBLE = (
    'Conditional energy-mass closure still excludes the following unmodeled '
    'mass items, so 12 in / 15 in rows must not be called whole-vehicle mass '
    'closure or a flyable result:'
)


def write_reports(
    config: AnalysisConfig,
    results: Sequence[PropulsionResult],
    output_dir: str | Path,
    generated_at: datetime | None = None,
    results_by_uncertainty: Mapping[str, Sequence[PropulsionResult]] | None = None,
) -> dict[str, Path]:
    """Write JSON, CSV, and Markdown into output_dir."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    stamp = generated_at or datetime.now(timezone.utc)
    stamp_text = stamp.astimezone(timezone.utc).isoformat()
    by_case = dict(results_by_uncertainty or {'nominal': results})
    payload = build_json_payload(config, results, stamp_text, by_case)
    json_path = out / JSON_NAME
    csv_path = out / CSV_NAME
    md_path = out / MARKDOWN_NAME
    json_path.write_text(
        json.dumps(payload, indent=2, sort_keys=False) + '\n',
        encoding='utf-8',
    )
    _write_csv(csv_path, _flatten_uncertainty_rows(by_case, results))
    md_path.write_text(
        render_markdown(config, results, stamp_text, by_case),
        encoding='utf-8',
    )
    return {'json': json_path, 'csv': csv_path, 'markdown': md_path}


def build_json_payload(
    config: AnalysisConfig,
    results: Sequence[PropulsionResult],
    generated_at: str,
    results_by_uncertainty: Mapping[str, Sequence[PropulsionResult]] | None = None,
) -> dict[str, Any]:
    """Full numeric snapshot plus banners."""
    by_case = dict(results_by_uncertainty or {'nominal': results})
    return {
        'status': STATUS_ANALYSIS_ONLY,
        'procurement_allowed': False,
        'not_for_procurement': STATUS_NOT_FOR_PROCUREMENT,
        'overall_propulsion_feasibility': STATUS_OVERALL_UNDETERMINED,
        'generated_at_utc': generated_at,
        'config_snapshot': _config_snapshot(config),
        'uncertainty_inputs': _uncertainty_snapshot(config),
        'equations': [
            {'name': name, 'equation': equation, 'unit': unit}
            for name, equation, unit in EQUATIONS
        ],
        'uncertainty_and_unmodeled': list(UNMODELED),
        'missing_closed_vehicle_mass_items': list(MISSING_CLOSED_VEHICLE_MASS_ITEMS),
        'n1_interpretation': N1_STATIC_FLAG,
        'results': [row.as_dict() for row in results],
        'results_by_uncertainty': {
            name: [row.as_dict() for row in rows]
            for name, rows in by_case.items()
        },
        'result_ranges': _result_ranges(by_case),
        'combined_current_baseline_gate_summary_nominal': _gate_summary(results),
        'any_conditional_candidate_nominal': _any_conditional_candidate(results),
        'any_conditional_candidate_by_uncertainty': {
            name: _any_conditional_candidate(by_case.get(name, ()))
            for name in REQUIRED_UNCERTAINTY_CASES
        },
        'combined_current_baseline_gate_summary_by_uncertainty': {
            name: _gate_summary(by_case.get(name, ()))
            for name in REQUIRED_UNCERTAINTY_CASES
        },
    }


def render_markdown(
    config: AnalysisConfig,
    results: Sequence[PropulsionResult],
    generated_at: str,
    results_by_uncertainty: Mapping[str, Sequence[PropulsionResult]] | None = None,
) -> str:
    """Human-review Markdown. Values only; never a procurement list."""
    by_case = dict(results_by_uncertainty or {'nominal': results})
    lines: list[str] = [
        '# Arachne-HX6 G1.5 Propulsion Feasibility',
        '',
        f'**{STATUS_ANALYSIS_ONLY}**',
        f'**{STATUS_NOT_FOR_PROCUREMENT}**',
        f'**overall_propulsion_feasibility: {STATUS_OVERALL_UNDETERMINED}**',
        '',
        f'- Generated (UTC): `{generated_at}`',
        f'- procurement_allowed: `{config.procurement_allowed}`',
        '- These numbers are planning calculations, not a buy list.',
        '- Energy-mass closure is not whole-vehicle feasibility or a flyable result.',
        '',
        '## Configuration input summary',
        '',
        '_All values are editable planning inputs, not measured data._',
        '',
        f'- notes: {config.notes}',
        f'- rotor_count: {config.rotor_count}',
        f'- gravity_m_s2: {config.gravity_m_s2}',
        f'- air_density_kg_m3: {config.air_density_kg_m3}',
        f'- thrust_to_weight_target: {config.thrust_to_weight_target}',
        f'- figure_of_merit: {config.figure_of_merit}',
        f'- motor_esc_efficiency: {config.motor_esc_efficiency}',
        f'- bus_voltage_v: {config.bus_voltage_v}',
        f'- avionics_power_w: {config.avionics_power_w}',
        f'- usable_fraction: {config.usable_fraction}',
        f'- pack_specific_energy_wh_kg: {config.pack_specific_energy_wh_kg}',
        f'- endurance_s: {config.endurance_s}',
        f'- mass_tolerance_kg: {config.mass_tolerance_kg}',
        f'- max_iterations: {config.max_iterations}',
        f'- current_motor_center_radius_m: {config.current_motor_center_radius_m}',
        f'- min_tip_clearance_m: {config.min_tip_clearance_m}',
        f'- propellers_inch: {", ".join(str(v) for v in config.propellers_inch)}',
        '',
        'Mass scenarios:',
        '',
    ]
    for scenario in config.mass_scenarios:
        lines.append(
            f'- `{scenario.name}`: {scenario.non_battery_mass_kg} kg non-battery. '
            f'{scenario.description}'
        )
    lines.extend([
        '',
        '## Uncertainty cases (planning bounds, not measured data)',
        '',
        '| case | rho (kg/m^3) | FoM | eta_drive | e_pack (Wh/kg) | '
        'usable_fraction | P_avionics (W) |',
        '|---|---:|---:|---:|---:|---:|---:|',
    ])
    for case in config.uncertainty_cases:
        lines.append(
            f'| `{case.name}` | {case.air_density_kg_m3:.3f} | '
            f'{case.figure_of_merit:.2f} | {case.motor_esc_efficiency:.2f} | '
            f'{case.pack_specific_energy_wh_kg:.1f} | {case.usable_fraction:.2f} | '
            f'{case.avionics_power_w:.1f} |'
        )
    lines.append('')
    for case in config.uncertainty_cases:
        lines.append(f'- `{case.name}`: {case.description}')
    lines.extend([
        '',
        '## Equations and units',
        '',
        '| Name | Equation | Unit |',
        '|---|---|---|',
    ])
    for name, equation, unit in EQUATIONS:
        lines.append(f'| `{name}` | `{equation}` | {unit} |')
    lines.extend([
        '',
        '## Uncertainty and unmodeled factors',
        '',
    ])
    for item in UNMODELED:
        lines.append(f'- {item}')
    lines.extend([
        '',
        '## Mass items not included in energy-mass closure',
        '',
        MISSING_MASS_PREAMBLE,
        '',
    ])
    for item in MISSING_CLOSED_VEHICLE_MASS_ITEMS:
        lines.append(f'- {item}')
    lines.extend([
        '',
        '## Nominal energy-mass closure',
        '',
        'Existence is analytic: a root exists only if `F(m_critical) <= 0`. '
        'The reported root is the smaller physical solution from bisection. '
        'Fixed-point iteration is a cross-check only.',
        '',
        'Infeasible rows leave closed-mass fields as `—`. Open-loop first-iteration '
        'values are diagnostic only.',
        '',
        '| scenario | D (in) | m_nb (kg) | m_batt (kg) | m_total (kg) | '
        'energy_mass_closure_status | m_crit (kg) | m_nb_max (kg) | '
        'closure_margin (kg) | root_method | root_iters | residual (kg) |',
        '|---|---:|---:|---:|---:|---|---:|---:|---:|---|---:|---:|',
    ])
    for row in results:
        lines.append(
            '| {name} | {din:.2f} | {mnb:.3f} | {mb} | {mt} | `{status}` | '
            '{mcrit:.3f} | {mnbmax:.3f} | {margin:.3f} | `{method}` | {it} | '
            '{resid} |'.format(
                name=row.scenario_name,
                din=row.diameter_inch,
                mnb=row.non_battery_mass_kg,
                mb=_md_num(row.battery_mass_kg, '.3f'),
                mt=_md_num(row.total_mass_kg, '.3f'),
                status=row.energy_mass_closure_status,
                mcrit=row.critical_total_mass_kg,
                mnbmax=row.maximum_non_battery_mass_for_closure_kg,
                margin=row.closure_margin_kg,
                method=row.root_method,
                it=row.root_iterations,
                resid=_md_num(row.residual_kg, '.3e'),
            )
        )
    lines.extend([
        '',
        '## Nominal hover performance (closed mass only)',
        '',
        '`battery_bus_current_a` is total DC input current at nominal bus '
        'voltage. It is not motor phase current.',
        '',
        '| scenario | D (in) | T (N) | T (kgf) | T_motor (N) | T_motor (kgf) | '
        'T_req@T/W (N) | T_req@T/W (kgf) | DL (N/m^2) | P_ideal (W) | '
        'P_ideal_motor (W) | P_elec (W) | I_bus (A) |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|',
    ])
    for row in results:
        lines.append(
            '| {name} | {din:.2f} | {T} | {Tkgf} | {Tm} | {Tmkgf} | {Treq} | '
            '{Treqkgf} | {dln} | {Pi} | {Pim} | {Pe} | {I} |'.format(
                name=row.scenario_name,
                din=row.diameter_inch,
                T=_md_num(row.hover_thrust_n, '.2f'),
                Tkgf=_md_num(row.hover_thrust_kgf, '.3f'),
                Tm=_md_num(row.hover_thrust_per_motor_n, '.2f'),
                Tmkgf=_md_num(row.hover_thrust_per_motor_kgf, '.3f'),
                Treq=_md_num(row.required_thrust_per_motor_at_target_tw_n, '.2f'),
                Treqkgf=_md_num(
                    row.required_thrust_per_motor_at_target_tw_kgf, '.3f'
                ),
                dln=_md_num(row.disk_loading_n_m2, '.1f'),
                Pi=_md_num(row.ideal_induced_power_w, '.1f'),
                Pim=_md_num(row.ideal_induced_power_per_motor_w, '.1f'),
                Pe=_md_num(row.electrical_hover_power_w, '.1f'),
                I=_md_num(row.battery_bus_current_a, '.2f'),
            )
        )
    lines.extend([
        '',
        '## Nominal current-skeleton combined gate',
        '',
        'The following table and candidate flag are **nominal only**. They do '
        'not represent conservative or optimistic planning bounds. Joint gate '
        'is `CONDITIONAL_CANDIDATE` only if the current 0.30 m radius '
        'can host the disk and energy-mass closure exists. Otherwise '
        '`REJECTED_FOR_CURRENT_BASELINE`. This is not a procurement or final '
        'flight-feasibility conclusion.',
        '',
        '| scenario | D (in) | current_geometry_fit | energy_mass_closure_status | '
        'combined_current_baseline_gate |',
        '|---|---:|---|---|---|',
    ])
    for row in results:
        lines.append(
            '| {name} | {din:.2f} | {fit} | `{estatus}` | `{gate}` |'.format(
                name=row.scenario_name,
                din=row.diameter_inch,
                fit='yes' if row.current_geometry_fit else 'NO',
                estatus=row.energy_mass_closure_status,
                gate=row.combined_current_baseline_gate,
            )
        )
    if _any_conditional_candidate(results):
        lines.append('')
        lines.append(
            '- Nominal: at least one row is a current-baseline conditional '
            'candidate.'
        )
    else:
        lines.append('')
        lines.append('- Nominal current skeleton has no combined candidate.')
    lines.extend([
        '',
        '## Combined gate by uncertainty case',
        '',
        'Each case is computed independently. A nominal non-candidate must not '
        'be read as a global result.',
        '',
        '| case | any_conditional_candidate |',
        '|---|---|',
    ])
    for name in REQUIRED_UNCERTAINTY_CASES:
        flag = _any_conditional_candidate(by_case.get(name, ()))
        lines.append(f'| `{name}` | `{flag}` |')
    lines.extend([
        '',
        '## N-1 static thrust reference',
        '',
        f'**{N1_STATIC_FLAG}**',
        '',
        'A real single-motor failure also depends on rotor layout, yaw moment, '
        'control allocation, remaining-motor saturation, and the flight stack. '
        'These static splits cannot prove safe fault-tolerant flight.',
        '',
        '| scenario | D (in) | T_motor (N) | T_n1 (N) | T_n1 (kgf) | '
        'burden increase | T_n1_req at T/W (N) |',
        '|---|---:|---:|---:|---:|---:|---:|',
    ])
    for row in results:
        lines.append(
            '| {name} | {din:.2f} | {Tm} | {Tn1} | {Tn1kgf} | {burden} | {Treq} |'.format(
                name=row.scenario_name,
                din=row.diameter_inch,
                Tm=_md_num(row.hover_thrust_per_motor_n, '.2f'),
                Tn1=_md_num(row.n1_hover_thrust_per_remaining_motor_n, '.2f'),
                Tn1kgf=_md_num(row.n1_hover_thrust_per_remaining_motor_kgf, '.3f'),
                burden=f'{row.n1_burden_increase_fraction:.2%}',
                Treq=_md_num(
                    row.n1_required_thrust_per_remaining_motor_at_target_tw_n, '.2f'
                ),
            )
        )
    lines.extend([
        '',
        '## Diagnostic open-loop values (not official closure results)',
        '',
        '| scenario | D (in) | diagnostic_first_iteration_battery_mass_kg | '
        'diagnostic_non_battery_mass_power_w | official m_batt | official m_total |',
        '|---|---:|---:|---:|---:|---:|',
    ])
    for row in results:
        lines.append(
            '| {name} | {din:.2f} | {db:.3f} | {dp:.1f} | {mb} | {mt} |'.format(
                name=row.scenario_name,
                din=row.diameter_inch,
                db=row.diagnostic_first_iteration_battery_mass_kg,
                dp=row.diagnostic_non_battery_mass_power_w,
                mb=_md_num(row.battery_mass_kg, '.3f'),
                mt=_md_num(row.total_mass_kg, '.3f'),
            )
        )
    lines.extend([
        '',
        '## Uncertainty ranges (same mass and diameter)',
        '',
        'Each cell is conservative / nominal / optimistic. `—` means that case '
        'has no energy-mass root.',
        '',
        '| scenario | D (in) | m_total (kg) | m_batt (kg) | energy_mass_closure_status | '
        'combined_current_baseline_gate |',
        '|---|---:|---|---|---|---|',
    ])
    for item in _result_ranges(by_case):
        lines.append(
            '| {name} | {din:.2f} | {mt} | {mb} | {st} | {gate} |'.format(
                name=item['scenario_name'],
                din=item['diameter_inch'],
                mt=_range_cell(item['total_mass_kg']),
                mb=_range_cell(item['battery_mass_kg']),
                st=_range_status_cell(item['energy_mass_closure_status']),
                gate=_range_status_cell(item['combined_current_baseline_gate']),
            )
        )
    lines.extend(['', '## Geometry conflicts', ''])
    conflicts = [row for row in results if not row.current_geometry_fit]
    if not conflicts:
        lines.append('- None of the compared diameters conflict with G1 R=0.30 m.')
    else:
        seen = []
        for row in conflicts:
            key = (row.diameter_inch, row.geometry_conflict)
            if key in seen:
                continue
            seen.append(key)
            lines.append(f'- {row.geometry_conflict}')
    lines.extend([
        '',
        '## Energy-mass closure notes',
        '',
        '- Ordinary fixed-point non-convergence is not treated as mathematical '
        'non-existence.',
        '- 12 in and 15 in rows that close are `CONDITIONAL_ENERGY_CLOSURE` only.',
        f'- `{STATUS_OVERALL_UNDETERMINED}`: propulsion feasibility of the whole '
        'vehicle remains undetermined.',
    ])
    infeasible = [
        row for row in results
        if not row.energy_mass_closure
    ]
    if infeasible:
        lines.append('- Rows with no energy-mass root:')
        for row in infeasible:
            lines.append(
                f'- `{row.scenario_name}` @ {row.diameter_inch} in: '
                f'{row.energy_mass_closure_status}; '
                f'closure_margin_kg={row.closure_margin_kg:.3f}'
            )
    lines.extend([
        '',
        f'**{STATUS_ANALYSIS_ONLY} / {STATUS_NOT_FOR_PROCUREMENT}**',
        '',
    ])
    return '\n'.join(lines)


def _config_snapshot(config: AnalysisConfig) -> dict[str, Any]:
    return {
        'status': config.status,
        'procurement_allowed': config.procurement_allowed,
        'overall_propulsion_feasibility': STATUS_OVERALL_UNDETERMINED,
        'notes': config.notes,
        'gravity_m_s2': config.gravity_m_s2,
        'air_density_kg_m3': config.air_density_kg_m3,
        'rotor_count': config.rotor_count,
        'thrust_to_weight_target': config.thrust_to_weight_target,
        'figure_of_merit': config.figure_of_merit,
        'motor_esc_efficiency': config.motor_esc_efficiency,
        'bus_voltage_v': config.bus_voltage_v,
        'avionics_power_w': config.avionics_power_w,
        'usable_fraction': config.usable_fraction,
        'pack_specific_energy_wh_kg': config.pack_specific_energy_wh_kg,
        'endurance_s': config.endurance_s,
        'mass_tolerance_kg': config.mass_tolerance_kg,
        'max_iterations': config.max_iterations,
        'current_motor_center_radius_m': config.current_motor_center_radius_m,
        'min_tip_clearance_m': config.min_tip_clearance_m,
        'battery_mass_fraction_warn': config.battery_mass_fraction_warn,
        'disk_loading_n_m2_warn': config.disk_loading_n_m2_warn,
        'propellers_inch': list(config.propellers_inch),
        'mass_scenarios': [
            {
                'name': scenario.name,
                'non_battery_mass_kg': scenario.non_battery_mass_kg,
                'description': scenario.description,
            }
            for scenario in config.mass_scenarios
        ],
    }


def _uncertainty_snapshot(config: AnalysisConfig) -> list[dict[str, Any]]:
    return [
        {
            'name': case.name,
            'planning_bound_not_measured': True,
            'air_density_kg_m3': case.air_density_kg_m3,
            'figure_of_merit': case.figure_of_merit,
            'motor_esc_efficiency': case.motor_esc_efficiency,
            'pack_specific_energy_wh_kg': case.pack_specific_energy_wh_kg,
            'usable_fraction': case.usable_fraction,
            'avionics_power_w': case.avionics_power_w,
            'description': case.description,
        }
        for case in config.uncertainty_cases
    ]


def _result_ranges(
    by_case: Mapping[str, Sequence[PropulsionResult]],
) -> list[dict[str, Any]]:
    nominal_rows = list(by_case.get('nominal', ()))
    if not nominal_rows:
        nominal_rows = next(iter(by_case.values()), ())
    keyed: dict[tuple[str, float], dict[str, PropulsionResult]] = {}
    for name, rows in by_case.items():
        for row in rows:
            key = (row.scenario_name, float(row.diameter_inch))
            keyed.setdefault(key, {})[name] = row
    ranges: list[dict[str, Any]] = []
    for row in nominal_rows:
        key = (row.scenario_name, float(row.diameter_inch))
        group = keyed.get(key, {})
        ranges.append({
            'scenario_name': row.scenario_name,
            'diameter_inch': row.diameter_inch,
            'total_mass_kg': _case_values(group, 'total_mass_kg'),
            'battery_mass_kg': _case_values(group, 'battery_mass_kg'),
            'energy_mass_closure_status': _case_values(
                group, 'energy_mass_closure_status'
            ),
            'combined_current_baseline_gate': _case_values(
                group, 'combined_current_baseline_gate'
            ),
            'battery_bus_current_a': _case_values(group, 'battery_bus_current_a'),
            'electrical_hover_power_w': _case_values(
                group, 'electrical_hover_power_w'
            ),
        })
    return ranges


def _case_values(
    group: Mapping[str, PropulsionResult],
    field_name: str,
) -> dict[str, Any]:
    values = {
        name: getattr(group[name], field_name) if name in group else None
        for name in ('conservative', 'nominal', 'optimistic')
    }
    numeric = [
        value for value in values.values()
        if isinstance(value, (int, float)) and not isinstance(value, bool)
    ]
    values['min'] = min(numeric) if numeric else None
    values['max'] = max(numeric) if numeric else None
    return values


def _any_conditional_candidate(results: Sequence[PropulsionResult]) -> bool:
    return any(
        row.combined_current_baseline_gate == GATE_CONDITIONAL_CANDIDATE
        for row in results
    )


def _gate_summary(results: Sequence[PropulsionResult]) -> dict[str, Any]:
    return {
        'any_conditional_candidate': _any_conditional_candidate(results),
        'rows': [
            {
                'scenario_name': row.scenario_name,
                'diameter_inch': row.diameter_inch,
                'current_geometry_fit': row.current_geometry_fit,
                'energy_mass_closure_status': row.energy_mass_closure_status,
                'combined_current_baseline_gate': row.combined_current_baseline_gate,
            }
            for row in results
        ],
    }


def _flatten_uncertainty_rows(
    by_case: Mapping[str, Sequence[PropulsionResult]],
    fallback: Sequence[PropulsionResult],
) -> list[PropulsionResult]:
    rows: list[PropulsionResult] = []
    if by_case:
        for name in ('conservative', 'nominal', 'optimistic'):
            rows.extend(by_case.get(name, ()))
        extra = [
            name for name in by_case
            if name not in ('conservative', 'nominal', 'optimistic')
        ]
        for name in extra:
            rows.extend(by_case[name])
        return rows
    return list(fallback)


def _md_num(value: float | None, fmt: str) -> str:
    if value is None:
        return MD_NULL
    return format(value, fmt)


def _range_cell(payload: Mapping[str, Any]) -> str:
    parts = []
    for name in ('conservative', 'nominal', 'optimistic'):
        value = payload.get(name)
        if isinstance(value, float):
            parts.append(f'{value:.3f}')
        elif value is None:
            parts.append(MD_NULL)
        else:
            parts.append(str(value))
    return ' / '.join(parts)


def _range_status_cell(payload: Mapping[str, Any]) -> str:
    parts = []
    for name in ('conservative', 'nominal', 'optimistic'):
        value = payload.get(name)
        parts.append(MD_NULL if value is None else str(value))
    return ' / '.join(parts)


def _csv_cell(value: Any) -> str:
    if value is None:
        return ''
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if isinstance(value, float):
        return repr(value) if abs(value) < 1.0e-3 and value != 0.0 else f'{value:.8f}'.rstrip('0').rstrip('.')
    return str(value)


def _write_csv(path: Path, results: Iterable[PropulsionResult]) -> None:
    fieldnames = [
        'status',
        'not_for_procurement',
        'procurement_allowed',
        'overall_propulsion_feasibility',
        'uncertainty_case',
        'scenario_name',
        'diameter_inch',
        'diameter_m',
        'non_battery_mass_kg',
        'battery_mass_kg',
        'total_mass_kg',
        'hover_thrust_n',
        'hover_thrust_kgf',
        'hover_thrust_per_motor_n',
        'hover_thrust_per_motor_kgf',
        'required_thrust_per_motor_at_target_tw_n',
        'required_thrust_per_motor_at_target_tw_kgf',
        'area_one_m2',
        'area_total_m2',
        'disk_loading_n_m2',
        'disk_loading_kg_m2',
        'ideal_induced_power_w',
        'ideal_induced_power_per_motor_w',
        'electrical_hover_power_w',
        'battery_bus_current_a',
        'adjacent_motor_center_m',
        'min_motor_center_radius_m',
        'rotor_envelope_diameter_at_current_r_m',
        'current_geometry_fit',
        'geometry_conflict',
        'energy_mass_closure',
        'energy_mass_closure_status',
        'critical_total_mass_kg',
        'maximum_non_battery_mass_for_closure_kg',
        'closure_margin_kg',
        'root_method',
        'root_iterations',
        'residual_kg',
        'diagnostic_first_iteration_battery_mass_kg',
        'diagnostic_non_battery_mass_power_w',
        'combined_current_baseline_gate',
        'n1_hover_thrust_per_remaining_motor_n',
        'n1_hover_thrust_per_remaining_motor_kgf',
        'n1_burden_increase_fraction',
        'n1_required_thrust_per_remaining_motor_at_target_tw_n',
        'n1_required_thrust_per_remaining_motor_at_target_tw_kgf',
        'n1_interpretation',
        'risk_flags',
    ]
    with path.open('w', encoding='utf-8', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in results:
            writer.writerow({
                'status': row.status,
                'not_for_procurement': STATUS_NOT_FOR_PROCUREMENT,
                'procurement_allowed': row.procurement_allowed,
                'overall_propulsion_feasibility': row.overall_propulsion_feasibility,
                'uncertainty_case': row.uncertainty_case,
                'scenario_name': row.scenario_name,
                'diameter_inch': f'{row.diameter_inch:.4f}',
                'diameter_m': f'{row.diameter_m:.6f}',
                'non_battery_mass_kg': f'{row.non_battery_mass_kg:.6f}',
                'battery_mass_kg': _csv_cell(row.battery_mass_kg),
                'total_mass_kg': _csv_cell(row.total_mass_kg),
                'hover_thrust_n': _csv_cell(row.hover_thrust_n),
                'hover_thrust_kgf': _csv_cell(row.hover_thrust_kgf),
                'hover_thrust_per_motor_n': _csv_cell(row.hover_thrust_per_motor_n),
                'hover_thrust_per_motor_kgf': _csv_cell(
                    row.hover_thrust_per_motor_kgf
                ),
                'required_thrust_per_motor_at_target_tw_n': _csv_cell(
                    row.required_thrust_per_motor_at_target_tw_n
                ),
                'required_thrust_per_motor_at_target_tw_kgf': _csv_cell(
                    row.required_thrust_per_motor_at_target_tw_kgf
                ),
                'area_one_m2': f'{row.area_one_m2:.8f}',
                'area_total_m2': f'{row.area_total_m2:.8f}',
                'disk_loading_n_m2': _csv_cell(row.disk_loading_n_m2),
                'disk_loading_kg_m2': _csv_cell(row.disk_loading_kg_m2),
                'ideal_induced_power_w': _csv_cell(row.ideal_induced_power_w),
                'ideal_induced_power_per_motor_w': _csv_cell(
                    row.ideal_induced_power_per_motor_w
                ),
                'electrical_hover_power_w': _csv_cell(row.electrical_hover_power_w),
                'battery_bus_current_a': _csv_cell(row.battery_bus_current_a),
                'adjacent_motor_center_m': f'{row.adjacent_motor_center_m:.6f}',
                'min_motor_center_radius_m': f'{row.min_motor_center_radius_m:.6f}',
                'rotor_envelope_diameter_at_current_r_m': (
                    f'{row.rotor_envelope_diameter_at_current_r_m:.6f}'
                ),
                'current_geometry_fit': row.current_geometry_fit,
                'geometry_conflict': row.geometry_conflict,
                'energy_mass_closure': row.energy_mass_closure,
                'energy_mass_closure_status': row.energy_mass_closure_status,
                'critical_total_mass_kg': f'{row.critical_total_mass_kg:.6f}',
                'maximum_non_battery_mass_for_closure_kg': (
                    f'{row.maximum_non_battery_mass_for_closure_kg:.6f}'
                ),
                'closure_margin_kg': f'{row.closure_margin_kg:.6f}',
                'root_method': row.root_method,
                'root_iterations': row.root_iterations,
                'residual_kg': _csv_cell(row.residual_kg),
                'diagnostic_first_iteration_battery_mass_kg': (
                    f'{row.diagnostic_first_iteration_battery_mass_kg:.6f}'
                ),
                'diagnostic_non_battery_mass_power_w': (
                    f'{row.diagnostic_non_battery_mass_power_w:.6f}'
                ),
                'combined_current_baseline_gate': row.combined_current_baseline_gate,
                'n1_hover_thrust_per_remaining_motor_n': _csv_cell(
                    row.n1_hover_thrust_per_remaining_motor_n
                ),
                'n1_hover_thrust_per_remaining_motor_kgf': _csv_cell(
                    row.n1_hover_thrust_per_remaining_motor_kgf
                ),
                'n1_burden_increase_fraction': (
                    f'{row.n1_burden_increase_fraction:.6f}'
                ),
                'n1_required_thrust_per_remaining_motor_at_target_tw_n': _csv_cell(
                    row.n1_required_thrust_per_remaining_motor_at_target_tw_n
                ),
                'n1_required_thrust_per_remaining_motor_at_target_tw_kgf': _csv_cell(
                    row.n1_required_thrust_per_remaining_motor_at_target_tw_kgf
                ),
                'n1_interpretation': row.n1_interpretation,
                'risk_flags': ','.join(row.risk_flags),
            })
