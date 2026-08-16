"""Markdown serialization of an ArchitectureResult.

Human-review text only. Values, banners, and table order are part of the
official report contract.

ANALYSIS_ONLY. NOT_FOR_PROCUREMENT.
"""

from __future__ import annotations

from arachne_hx6_analysis.architecture import (
    ARCH_GATE_REJECTED_ENERGY_CLOSURE,
    ARCH_GATE_REJECTED_GEOMETRY,
    ARCH_GATE_UNDETERMINED_MASS_LEDGER,
    ARCH_GATE_UNDETERMINED_MODEL_LIMITATION,
    FORBIDDEN_ARCHITECTURE_STATUS_WORDS,
    GATE_CLEARANCE_MET,
    REQUIRED_JOINT_NAMES,
    TRANSITION_PROOF_FLAG,
    ArchitectureResult,
)
from arachne_hx6_analysis.architecture_report_payload import (
    EQUATIONS,
    _gate_summary_by_uncertainty,
    _unique_limitations,
    _unique_reasons,
)
from arachne_hx6_analysis.model import (
    REQUIRED_UNCERTAINTY_CASES,
    STATUS_ANALYSIS_ONLY,
    STATUS_NOT_FOR_PROCUREMENT,
    STATUS_OVERALL_UNDETERMINED,
)

MD_NULL = '—'

def render_architecture_markdown(
    result: ArchitectureResult,
    generated_at: str,
) -> str:
    """Human-review Markdown. Values only; never a procurement list."""
    config = result.config
    lines: list[str] = [
        '# Arachne-HX6 G2 Architecture Envelope',
        '',
        f'**{STATUS_ANALYSIS_ONLY}**',
        f'**{STATUS_NOT_FOR_PROCUREMENT}**',
        f'**overall_architecture_feasibility: {STATUS_OVERALL_UNDETERMINED}**',
        f'**mass_ledger_status: {result.mass_ledger_status}**',
        f'**stow_requirements_status: {result.stow_requirements_status}**',
        f'**stow_pose_evidence_status: {result.stow_pose_evidence_status}**',
        f'**stow_pose_is_hardware_validated: {str(result.stow_pose_is_hardware_validated).lower()}**',
        f'**robust_geometry_status: {result.robust_geometry_status}**',
        f'**{TRANSITION_PROOF_FLAG}**',
        '',
        f'- Generated (UTC): `{generated_at}`',
        f'- procurement_allowed: `{config.procurement_allowed}`',
        '- Geometry pass is not energy-mass closure.',
        '- Conditional energy-mass closure is not whole-vehicle mass closure.',
        '- Discrete leg sampling is not a full configuration-space proof.',
        '- No real hardware data. Structure must not be frozen. Purchase is not allowed.',
        '',
        '## Configuration input summary',
        '',
        '_All values are editable planning inputs, not measured data._',
        '',
        f'- notes: {config.notes}',
        f'- rotor_count: {config.rotor_count}',
        f'- propeller_diameters_in: {", ".join(_fmt_in(v) for v in config.propeller_diameters_in)}',
        f'- motor_center_radii_m: {", ".join(_fmt_m(v) for v in config.motor_center_radii_m)}',
        f'- min_tip_clearance_m: {config.min_tip_clearance_m}',
        f'- min_body_clearance_m: {config.min_body_clearance_m}',
        f'- min_sensor_pod_clearance_m: {config.min_sensor_pod_clearance_m}',
        f'- min_leg_clearance_m: {config.min_leg_clearance_m}',
        f'- leg_sweep.sample_count: {config.sample_count}',
        f'- analysis_stowed.pose_kind: `{config.analysis_stowed_pose_kind}`',
        f'- geometry_uncertainty_allowance_m: {_md_num(config.geometry_uncertainty_allowance_m, ".6f")}',
        '- stow_requirements: all current limits are unspecified (`null`).',
        '',
        '## G1 baseline consistency',
        '',
        f'- consistent: `{result.baseline.consistent}`',
        f'- xacro: `{result.baseline.xacro_path}`',
        f'- standing_pose: `{result.baseline.standing_pose_path}`',
        '',
        '| field | YAML (m) | Xacro/derived (m) | match |',
        '|---|---:|---:|---|',
    ]
    for item in result.baseline.comparisons:
        lines.append(
            f'| `{item["field"]}` | {item["yaml_m"]:.6f} | {item["xacro_m"]:.6f} | '
            f'{"yes" if item["match"] else "NO"} |'
        )
    lines.extend([
        '',
        '## analysis_stowed (ANALYSIS_POSE_ONLY / UNQUALIFIED_ANALYSIS_POSE)',
        '',
        config.analysis_stowed_notes,
        '',
        f'- stow_pose_evidence_status: `{result.stow_pose_evidence_status}`',
        f'- stow_requirements_status: `{result.stow_requirements_status}`',
        f'- stow_pose_is_hardware_validated: `{str(result.stow_pose_is_hardware_validated).lower()}`',
        '- This pose only proves that one analysis path can be computed. '
        'It does not prove flight-stow requirements, locking requirements, '
        'or mechanical realizability.',
        '',
        '| requirement | value |',
        '|---|---|',
    ])
    for key, value in result.config.stow_requirements.as_dict().items():
        lines.append(f'| `{key}` | {_md_num(value, ".6f")} |')
    lines.extend([
        '',
        '| joint | standing (rad) | analysis_stowed (rad) |',
        '|---|---:|---:|',
    ])
    for name in REQUIRED_JOINT_NAMES:
        lines.append(
            f'| `{name}` | {result.standing_joints[name]:.3f} | '
            f'{result.analysis_stowed_joints[name]:.3f} |'
        )
    lines.extend([
        '',
        '## Analysis-pose envelope reduction (not a stow pass)',
        '',
        'Height and planform come from the union AABB of rotors, body, '
        'sensor pods, camera, and leg capsules. A smaller analysis-pose '
        'envelope does not mean the pose satisfies flight-stow requirements.',
        '',
        '| D (in) | R (m) | standing H (m) | analysis H (m) | dH (m) | dH ratio | '
        'standing leg-below-body (m) | analysis leg-below-body (m) | '
        'standing L/W (m) | analysis L/W (m) | rotor-plane to lowest analysis leg (m) |',
        '|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---:|',
    ])
    for row in result.geometry_candidates:
        lines.append(
            '| {din} | {r} | {sh} | {ah} | {dh} | {ratio:.6f} | {slb} | {alb} | '
            '{sl} / {sw} | {al} / {aw} | {rp} |'.format(
                din=_fmt_in(row.diameter_inch),
                r=_fmt_m(row.motor_center_radius_m),
                sh=_fmt_m(row.standing_total_height_m),
                ah=_fmt_m(row.analysis_pose_total_height_m),
                dh=_fmt_m(row.height_reduction_m),
                ratio=row.height_reduction_ratio,
                slb=_fmt_m(row.standing_leg_below_body_m),
                alb=_fmt_m(row.analysis_pose_leg_below_body_m),
                sl=_fmt_m(row.standing_planform_length_m),
                sw=_fmt_m(row.standing_planform_width_m),
                al=_fmt_m(row.analysis_pose_planform_length_m),
                aw=_fmt_m(row.analysis_pose_planform_width_m),
                rp=_fmt_m(row.rotor_plane_to_lowest_leg_point_m),
            )
        )
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
        'Segment-to-disk unsigned distance is returned only after a Lipschitz '
        'error certificate: `upper_bound - lower_bound <= '
        'geometry_solver_tolerance_m`. Reaching the evaluation budget without '
        'that certificate is fail-closed: the solver raises, no distance is '
        'returned, and `CLEARANCE_MET` is not assigned from an uncertified gap.',
        '',
        '## Geometry candidate matrix',
        '',
        'Rows are generated from the YAML diameter × radius lists. '
        'They are not hard-coded results.',
        '',
        '| D (in) | R (m) | d_adj (m) | tip gap (m) | R_min (m) | D_env (m) | '
        'rotor_spacing | body gap (m) | body | pod gap (m) | sensor_pod | '
        'sweep min (m) | sweep | standing L/W/H (m) | stowed L/W/H (m) |',
        '|---:|---:|---:|---:|---:|---:|---|---:|---|---:|---|---:|---|---|---|',
    ])
    for row in result.geometry_candidates:
        sweep = row.sampled_leg_sweep
        lines.append(
            '| {din} | {r} | {adj} | {tip} | {rmin} | {env} | `{space}` | {body} | '
            '`{bg}` | {pod} | `{pg}` | {sweep} | `{sg}` | {sl} / {sw} / {sh} | '
            '{tl} / {tw} / {th} |'.format(
                din=_fmt_in(row.diameter_inch),
                r=_fmt_m(row.motor_center_radius_m),
                adj=_fmt_m(row.adjacent_motor_center_m),
                tip=_fmt_m(row.adjacent_rotor_tip_clearance_m),
                rmin=_fmt_m(row.min_motor_center_radius_m),
                env=_fmt_m(row.rotor_envelope_diameter_m),
                space=row.rotor_spacing_gate,
                body=_fmt_m(row.body_clearance_m),
                bg=row.body_clearance_gate,
                pod=_fmt_m(row.sensor_pod_clearance_m),
                pg=row.sensor_pod_clearance_gate,
                sweep=_fmt_m(sweep.min_clearance_m),
                sg=(
                    GATE_CLEARANCE_MET
                    if not sweep.below_threshold
                    else 'CLEARANCE_NOT_MET'
                ),
                sl=_fmt_m(row.standing_envelope['length_m']),
                sw=_fmt_m(row.standing_envelope['width_m']),
                sh=_fmt_m(row.standing_envelope['height_m']),
                tl=_fmt_m(row.analysis_stowed_envelope['length_m']),
                tw=_fmt_m(row.analysis_stowed_envelope['width_m']),
                th=_fmt_m(row.analysis_stowed_envelope['height_m']),
            )
        )
    lines.extend([
        '',
        '## Standing to analysis_stowed sampled sweep',
        '',
        f'**{TRANSITION_PROOF_FLAG}**',
        '',
        f'- sample_count: {config.sample_count}',
        '- Endpoints are standing (i=0) and analysis_stowed (i=N-1).',
        '',
        '| D (in) | R (m) | min gap (m) | worst i | worst s | worst segment | '
        'worst rotor | start gap (m) | end gap (m) | below threshold |',
        '|---:|---:|---:|---:|---:|---|---|---:|---:|---|',
    ])
    for row in result.geometry_candidates:
        sweep = row.sampled_leg_sweep
        lines.append(
            '| {din} | {r} | {gap} | {idx} | {frac:.3f} | `{seg}` | `{rot}` | '
            '{start} | {end} | {below} |'.format(
                din=_fmt_in(row.diameter_inch),
                r=_fmt_m(row.motor_center_radius_m),
                gap=_fmt_m(sweep.min_clearance_m),
                idx=sweep.worst_sample_index,
                frac=sweep.worst_path_fraction,
                seg=sweep.worst_leg_segment,
                rot=sweep.worst_rotor,
                start=_fmt_m(sweep.start_clearance_m),
                end=_fmt_m(sweep.end_clearance_m),
                below='yes' if sweep.below_threshold else 'no',
            )
        )
    lines.extend([
        '',
        '## Joint gating (uncertainty × mass scenario × D × R)',
        '',
        'Energy-mass status is reused from the G1.5 public solver. '
        'G1.5 7.16 / 12 / 16 kg values remain overall planning boundaries, '
        'not a completed parts ledger. A candidate with R != 0.30 m is not '
        'whole-vehicle energy closure: arm-extension mass is unmodeled.',
        '',
        'architecture_gate uses only '
        f'`{ARCH_GATE_REJECTED_GEOMETRY}`, '
        f'`{ARCH_GATE_REJECTED_ENERGY_CLOSURE}`, '
        f'`{ARCH_GATE_UNDETERMINED_MASS_LEDGER}`, '
        f'`{ARCH_GATE_UNDETERMINED_MODEL_LIMITATION}`.',
        '',
        '| case | scenario | D (in) | R (m) | nominal_geom | robust_geom | '
        'energy_mass_closure_status | mass_ledger | stow_req | arm_mass | '
        'architecture_gate |',
        '|---|---|---:|---:|---|---|---|---|---|---|---|',
    ])
    for row in result.joint_gate_rows:
        lines.append(
            '| `{case}` | `{scen}` | {din} | {r} | `{ng}` | `{rg}` | '
            '`{en}` | `{ms}` | `{st}` | `{arm}` | `{ag}` |'.format(
                case=row.uncertainty_case,
                scen=row.scenario_name,
                din=_fmt_in(row.diameter_inch),
                r=_fmt_m(row.motor_center_radius_m),
                ng=row.nominal_geometry_status,
                rg=row.robust_geometry_status,
                en=row.energy_mass_closure_status,
                ms=row.mass_ledger_status,
                st=row.stow_requirements_status,
                arm=row.arm_radius_mass_coupling_status,
                ag=row.architecture_gate,
            )
        )
    lines.extend([
        '',
        '## Combined gate by uncertainty case',
        '',
        '| case | rows | REJECTED_GEOMETRY | REJECTED_ENERGY_CLOSURE | '
        'UNDETERMINED_MASS_LEDGER | UNDETERMINED_MODEL_LIMITATION |',
        '|---|---:|---:|---:|---:|---:|',
    ])
    summary = _gate_summary_by_uncertainty(result)
    for name in REQUIRED_UNCERTAINTY_CASES:
        item = summary[name]
        lines.append(
            f'| `{name}` | {item["rows"]} | {item[ARCH_GATE_REJECTED_GEOMETRY]} | '
            f'{item[ARCH_GATE_REJECTED_ENERGY_CLOSURE]} | '
            f'{item[ARCH_GATE_UNDETERMINED_MASS_LEDGER]} | '
            f'{item[ARCH_GATE_UNDETERMINED_MODEL_LIMITATION]} |'
        )
    lines.extend([
        '',
        '## Mass evidence ledger',
        '',
        f'- mass_ledger_status: `{result.mass_ledger_status}`',
        '- Unknown official masses are `—` here, `null` in JSON, and empty in CSV.',
        '- G1.5 scenario masses are not copied into this ledger.',
        '',
        '| id | evidence_status | mass_kg | source_kind | notes |',
        '|---|---|---:|---|---|',
    ])
    for item in result.mass_ledger_items:
        lines.append(
            f'| `{item.item_id}` | `{item.evidence_status}` | '
            f'{_md_num(item.mass_kg, ".3f")} | `{item.source_kind}` | {item.notes} |'
        )
    lines.extend([
        '',
        '## Rejection reasons',
        '',
    ])
    reasons = _unique_reasons(result.joint_gate_rows)
    if not reasons:
        lines.append('- None recorded.')
    else:
        for reason in reasons:
            lines.append(f'- `{reason}`')
    lines.extend([
        '',
        '## Limitation reasons',
        '',
    ])
    limitations = _unique_limitations(result.joint_gate_rows)
    if not limitations:
        lines.append('- None recorded.')
    else:
        for reason in limitations:
            lines.append(f'- `{reason}`')
    lines.extend([
        '',
        '## Unmodeled factors',
        '',
    ])
    for item in result.unmodeled:
        lines.append(f'- {item}')
    lines.extend([
        '',
        '## Diagnostic block (not official closure fields)',
        '',
        f'- energy_rows_solved: {result.diagnostic.get("energy_rows_solved")}',
        f'- geometry_candidate_count: {result.diagnostic.get("geometry_candidate_count")}',
        f'- joint_gate_row_count: {result.diagnostic.get("joint_gate_row_count")}',
        f'- path_sample_count: {result.diagnostic.get("path_sample_count")}',
        '- Official architecture_gate never uses '
        + ', '.join(f'`{word}`' for word in FORBIDDEN_ARCHITECTURE_STATUS_WORDS)
        + '.',
        '',
        f'**{STATUS_ANALYSIS_ONLY} / {STATUS_NOT_FOR_PROCUREMENT}**',
        f'**overall_architecture_feasibility: {STATUS_OVERALL_UNDETERMINED}**',
        f'**mass_ledger_status: {result.mass_ledger_status}**',
        f'**stow_requirements_status: {result.stow_requirements_status}**',
        f'**robust_geometry_status: {result.robust_geometry_status}**',
        '',
    ])
    return '\n'.join(lines)



def _fmt_in(value: float) -> str:
    text = f'{value:.4f}'.rstrip('0').rstrip('.')
    return text


def _fmt_m(value: float) -> str:
    return f'{value:.6f}'


def _md_num(value: float | None, fmt: str) -> str:
    if value is None:
        return MD_NULL
    return format(value, fmt)
