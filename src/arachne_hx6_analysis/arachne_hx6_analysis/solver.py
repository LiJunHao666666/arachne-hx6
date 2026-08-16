"""Load YAML planning inputs and solve coupled hover / battery mass.

Energy-mass closure uses an analytic existence test on F(m) and a
bisection root. Fixed-point iteration is a cross-check only.

ANALYSIS_ONLY. NOT_FOR_PROCUREMENT.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any, Mapping
import math

import yaml

from arachne_hx6_analysis.inputs import (
    as_bool as _as_bool,
    as_float as _as_float,
    as_int as _as_int,
    as_list as _as_list,
    as_mapping as _as_mapping,
    as_str as _as_str,
    optional_str as _optional_str,
    require_key as _require_key,
)
from arachne_hx6_analysis.model import (
    GATE_CONDITIONAL_CANDIDATE,
    GATE_REJECTED_FOR_CURRENT_BASELINE,
    MISSING_CLOSED_VEHICLE_MASS_ITEMS,
    N1_STATIC_FLAG,
    REQUIRED_UNCERTAINTY_CASES,
    ROOT_METHOD_BISECTION,
    ROOT_METHOD_NONE,
    STATUS_ANALYSIS_ONLY,
    STATUS_CONDITIONAL_ENERGY_CLOSURE,
    STATUS_ENERGY_MASS_CLOSURE_INFEASIBLE,
    STATUS_NOT_FOR_PROCUREMENT,
    STATUS_OVERALL_UNDETERMINED,
    AnalysisConfig,
    ConvergenceError,
    InvalidInputError,
    MassScenario,
    UncertaintyCase,
    adjacent_motor_center_distance_m,
    avionics_battery_mass_kg,
    battery_bus_current_a,
    critical_total_mass_kg,
    disk_loading_kg_m2,
    disk_loading_n_m2,
    electrical_hover_power_w,
    energy_mass_coupling_coefficient,
    energy_mass_residual_kg,
    hover_energy_to_battery_mass_factor,
    hover_thrust_n,
    hover_thrust_per_motor_n,
    inches_to_metres,
    maximum_non_battery_mass_for_closure_kg,
    min_motor_center_radius_m,
    n1_burden_increase_fraction,
    n1_hover_thrust_per_remaining_motor_n,
    n1_required_thrust_per_remaining_motor_at_target_tw_n,
    newtons_to_kgf,
    required_thrust_per_motor_at_target_tw_n,
    required_battery_mass_kg,
    rotor_disk_area_m2,
    rotor_envelope_diameter_m,
    total_ideal_induced_power_w,
    total_rotor_disk_area_m2,
)


@dataclass(frozen=True)
class PropulsionResult:
    """One uncertainty × mass-scenario × propeller row."""

    status: str
    procurement_allowed: bool
    overall_propulsion_feasibility: str
    uncertainty_case: str
    scenario_name: str
    scenario_description: str
    diameter_inch: float
    diameter_m: float
    non_battery_mass_kg: float
    battery_mass_kg: float | None
    total_mass_kg: float | None
    rotor_count: int
    area_one_m2: float
    area_total_m2: float
    hover_thrust_n: float | None
    hover_thrust_kgf: float | None
    hover_thrust_per_motor_n: float | None
    hover_thrust_per_motor_kgf: float | None
    required_thrust_per_motor_at_target_tw_n: float | None
    required_thrust_per_motor_at_target_tw_kgf: float | None
    disk_loading_n_m2: float | None
    disk_loading_kg_m2: float | None
    ideal_induced_power_w: float | None
    ideal_induced_power_per_motor_w: float | None
    electrical_hover_power_w: float | None
    battery_bus_current_a: float | None
    battery_bus_current_note: str
    adjacent_motor_center_m: float
    min_motor_center_radius_m: float
    rotor_envelope_diameter_at_current_r_m: float
    rotor_envelope_diameter_at_min_r_m: float
    current_motor_center_radius_m: float
    current_geometry_fit: bool
    geometry_conflict: str
    battery_mass_fraction: float | None
    energy_mass_closure: bool
    energy_mass_closure_status: str
    critical_total_mass_kg: float
    maximum_non_battery_mass_for_closure_kg: float
    closure_margin_kg: float
    root_method: str
    root_iterations: int
    residual_kg: float | None
    diagnostic_first_iteration_battery_mass_kg: float
    diagnostic_non_battery_mass_power_w: float
    combined_current_baseline_gate: str
    n1_hover_thrust_per_remaining_motor_n: float | None
    n1_hover_thrust_per_remaining_motor_kgf: float | None
    n1_burden_increase_fraction: float
    n1_required_thrust_per_remaining_motor_at_target_tw_n: float | None
    n1_required_thrust_per_remaining_motor_at_target_tw_kgf: float | None
    n1_interpretation: str
    fixed_point_crosscheck_converged: bool | None
    fixed_point_crosscheck_total_mass_kg: float | None
    missing_closed_vehicle_mass_items: tuple[str, ...]
    risk_flags: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data['risk_flags'] = list(self.risk_flags)
        data['missing_closed_vehicle_mass_items'] = list(
            self.missing_closed_vehicle_mass_items
        )
        return data


_BUS_CURRENT_NOTE = (
    'battery_bus_current_a is total DC input current at the planning '
    'nominal bus voltage (P_elec / V_bus). It is not a per-motor phase '
    'current and does not model voltage sag, wiring loss, or peak current. '
    'ideal_induced_power_per_motor_w is a momentum-theory mechanical '
    'reference and must not be converted into a claimed motor current.'
)


def load_analysis_config(path: str | Path) -> AnalysisConfig:
    """Parse a planning YAML file and validate it."""
    config_path = Path(path)
    if not config_path.is_file():
        raise InvalidInputError(f'config file not found: {config_path}')
    try:
        raw = yaml.safe_load(config_path.read_text(encoding='utf-8'))
    except yaml.YAMLError as exc:
        raise InvalidInputError(f'invalid YAML in {config_path}: {exc}') from exc
    try:
        config = _parse_analysis_config(raw)
    except InvalidInputError:
        raise
    except KeyError as exc:
        raise InvalidInputError(f'config missing key: {exc}') from exc
    except (TypeError, ValueError) as exc:
        raise InvalidInputError(f'invalid config value: {exc}') from exc
    config.validate()
    return config


def _parse_analysis_config(raw: Any) -> AnalysisConfig:
    root = _as_mapping(raw, 'config root')
    constants = _as_mapping(_require_key(root, 'constants'), 'constants')
    propulsion = _as_mapping(_require_key(root, 'propulsion'), 'propulsion')
    battery = _as_mapping(_require_key(root, 'battery'), 'battery')
    solver = _as_mapping(_require_key(root, 'solver'), 'solver')
    geometry = _as_mapping(_require_key(root, 'geometry'), 'geometry')
    risk_flags = _as_mapping(_require_key(root, 'risk_flags'), 'risk_flags')
    scenarios_raw = _as_list(
        _require_key(root, 'mass_scenarios'), 'mass_scenarios'
    )
    propellers_raw = _as_list(
        _require_key(root, 'propellers_inch'), 'propellers_inch'
    )
    uncertainty_raw = _as_mapping(
        _require_key(root, 'uncertainty_cases'), 'uncertainty_cases'
    )
    return AnalysisConfig(
        status=_as_str(_require_key(root, 'status'), 'status'),
        procurement_allowed=_as_bool(
            _require_key(root, 'procurement_allowed'), 'procurement_allowed'
        ),
        notes=_optional_str(root.get('notes', ''), 'notes'),
        gravity_m_s2=_as_float(
            _require_key(constants, 'gravity_m_s2', 'constants'),
            'constants.gravity_m_s2',
        ),
        air_density_kg_m3=_as_float(
            _require_key(constants, 'air_density_kg_m3', 'constants'),
            'constants.air_density_kg_m3',
        ),
        rotor_count=_as_int(
            _require_key(constants, 'rotor_count', 'constants'),
            'constants.rotor_count',
        ),
        thrust_to_weight_target=_as_float(
            _require_key(propulsion, 'thrust_to_weight_target', 'propulsion'),
            'propulsion.thrust_to_weight_target',
        ),
        figure_of_merit=_as_float(
            _require_key(propulsion, 'figure_of_merit', 'propulsion'),
            'propulsion.figure_of_merit',
        ),
        motor_esc_efficiency=_as_float(
            _require_key(propulsion, 'motor_esc_efficiency', 'propulsion'),
            'propulsion.motor_esc_efficiency',
        ),
        bus_voltage_v=_as_float(
            _require_key(propulsion, 'bus_voltage_v', 'propulsion'),
            'propulsion.bus_voltage_v',
        ),
        avionics_power_w=_as_float(
            _require_key(propulsion, 'avionics_power_w', 'propulsion'),
            'propulsion.avionics_power_w',
        ),
        usable_fraction=_as_float(
            _require_key(battery, 'usable_fraction', 'battery'),
            'battery.usable_fraction',
        ),
        pack_specific_energy_wh_kg=_as_float(
            _require_key(battery, 'pack_specific_energy_wh_kg', 'battery'),
            'battery.pack_specific_energy_wh_kg',
        ),
        endurance_s=_as_float(
            _require_key(battery, 'endurance_s', 'battery'),
            'battery.endurance_s',
        ),
        mass_tolerance_kg=_as_float(
            _require_key(solver, 'mass_tolerance_kg', 'solver'),
            'solver.mass_tolerance_kg',
        ),
        max_iterations=_as_int(
            _require_key(solver, 'max_iterations', 'solver'),
            'solver.max_iterations',
        ),
        current_motor_center_radius_m=_as_float(
            _require_key(
                geometry, 'current_motor_center_radius_m', 'geometry'
            ),
            'geometry.current_motor_center_radius_m',
        ),
        min_tip_clearance_m=_as_float(
            _require_key(geometry, 'min_tip_clearance_m', 'geometry'),
            'geometry.min_tip_clearance_m',
        ),
        battery_mass_fraction_warn=_as_float(
            _require_key(
                risk_flags, 'battery_mass_fraction_warn', 'risk_flags'
            ),
            'risk_flags.battery_mass_fraction_warn',
        ),
        disk_loading_n_m2_warn=_as_float(
            _require_key(risk_flags, 'disk_loading_n_m2_warn', 'risk_flags'),
            'risk_flags.disk_loading_n_m2_warn',
        ),
        propellers_inch=_parse_propellers_inch(propellers_raw),
        mass_scenarios=_parse_mass_scenarios(scenarios_raw),
        uncertainty_cases=_parse_uncertainty_cases(uncertainty_raw),
        raw=root,
    )


def _parse_propellers_inch(raw_values: list[Any]) -> tuple[float, ...]:
    diameters: list[float] = []
    seen: set[float] = set()
    for index, value in enumerate(raw_values):
        diameter = _as_float(value, f'propellers_inch[{index}]')
        if diameter in seen:
            raise InvalidInputError(
                f'duplicate propeller diameter: {diameter}'
            )
        seen.add(diameter)
        diameters.append(diameter)
    return tuple(diameters)


def _parse_mass_scenarios(raw_items: list[Any]) -> tuple[MassScenario, ...]:
    scenarios: list[MassScenario] = []
    seen_names: set[str] = set()
    for index, item in enumerate(raw_items):
        path = f'mass_scenarios[{index}]'
        mapping = _as_mapping(item, path)
        name = _as_str(_require_key(mapping, 'name', path), f'{path}.name').strip()
        if not name:
            raise InvalidInputError(f'{path}.name must be non-empty')
        if name in seen_names:
            raise InvalidInputError(f'duplicate mass scenario name: {name!r}')
        seen_names.add(name)
        description = _optional_str(
            mapping.get('description', ''), f'{path}.description'
        )
        scenarios.append(
            MassScenario(
                name=name,
                non_battery_mass_kg=_as_float(
                    _require_key(mapping, 'non_battery_mass_kg', path),
                    f'{path}.non_battery_mass_kg',
                ),
                description=description,
            )
        )
    return tuple(scenarios)


def _parse_uncertainty_cases(raw_cases: Mapping[str, Any]) -> tuple[UncertaintyCase, ...]:
    cases: list[UncertaintyCase] = []
    for name in REQUIRED_UNCERTAINTY_CASES:
        path = f'uncertainty_cases.{name}'
        if name not in raw_cases:
            raise InvalidInputError(
                f'uncertainty_cases missing required case {name!r}'
            )
        item = _as_mapping(raw_cases[name], path)
        try:
            cases.append(
                UncertaintyCase(
                    name=name,
                    air_density_kg_m3=_as_float(
                        item['air_density_kg_m3'],
                        f'{path}.air_density_kg_m3',
                    ),
                    figure_of_merit=_as_float(
                        item['figure_of_merit'], f'{path}.figure_of_merit'
                    ),
                    motor_esc_efficiency=_as_float(
                        item['motor_esc_efficiency'],
                        f'{path}.motor_esc_efficiency',
                    ),
                    pack_specific_energy_wh_kg=_as_float(
                        item['pack_specific_energy_wh_kg'],
                        f'{path}.pack_specific_energy_wh_kg',
                    ),
                    usable_fraction=_as_float(
                        item['usable_fraction'], f'{path}.usable_fraction'
                    ),
                    avionics_power_w=_as_float(
                        item['avionics_power_w'], f'{path}.avionics_power_w'
                    ),
                    description=_optional_str(
                        item.get('description', ''), f'{path}.description'
                    ),
                )
            )
        except KeyError as exc:
            raise InvalidInputError(f'{path} missing key: {exc}') from exc
    return tuple(cases)


def apply_uncertainty_case(
    config: AnalysisConfig,
    case: UncertaintyCase,
) -> AnalysisConfig:
    """Overlay one named planning bound set onto the loaded config."""
    overlaid = replace(
        config,
        air_density_kg_m3=case.air_density_kg_m3,
        figure_of_merit=case.figure_of_merit,
        motor_esc_efficiency=case.motor_esc_efficiency,
        pack_specific_energy_wh_kg=case.pack_specific_energy_wh_kg,
        usable_fraction=case.usable_fraction,
        avionics_power_w=case.avionics_power_w,
    )
    overlaid.validate()
    return overlaid


def evaluate_hover_at_mass(
    config: AnalysisConfig,
    total_mass_kg: float,
    diameter_inch: float,
) -> dict[str, float]:
    """Hover metrics at a frozen total mass. No battery iteration."""
    config.validate()
    diameter_m = inches_to_metres(diameter_inch)
    area_one = rotor_disk_area_m2(diameter_m)
    area_total = total_rotor_disk_area_m2(diameter_m, config.rotor_count)
    thrust = hover_thrust_n(total_mass_kg, config.gravity_m_s2)
    thrust_motor = hover_thrust_per_motor_n(
        total_mass_kg, config.gravity_m_s2, config.rotor_count
    )
    thrust_req = required_thrust_per_motor_at_target_tw_n(
        total_mass_kg,
        config.gravity_m_s2,
        config.rotor_count,
        config.thrust_to_weight_target,
    )
    ideal_power = total_ideal_induced_power_w(
        thrust, diameter_m, config.rotor_count, config.air_density_kg_m3
    )
    electrical_power = electrical_hover_power_w(
        ideal_power,
        config.figure_of_merit,
        config.motor_esc_efficiency,
        config.avionics_power_w,
    )
    return {
        'diameter_m': diameter_m,
        'area_one_m2': area_one,
        'area_total_m2': area_total,
        'hover_thrust_n': thrust,
        'hover_thrust_kgf': newtons_to_kgf(thrust, config.gravity_m_s2),
        'hover_thrust_per_motor_n': thrust_motor,
        'hover_thrust_per_motor_kgf': newtons_to_kgf(
            thrust_motor, config.gravity_m_s2
        ),
        'required_thrust_per_motor_at_target_tw_n': thrust_req,
        'required_thrust_per_motor_at_target_tw_kgf': newtons_to_kgf(
            thrust_req, config.gravity_m_s2
        ),
        'disk_loading_n_m2': disk_loading_n_m2(thrust, area_total),
        'disk_loading_kg_m2': disk_loading_kg_m2(total_mass_kg, area_total),
        'ideal_induced_power_w': ideal_power,
        'ideal_induced_power_per_motor_w': ideal_power / float(config.rotor_count),
        'electrical_hover_power_w': electrical_power,
        'battery_bus_current_a': battery_bus_current_a(
            electrical_power, config.bus_voltage_v
        ),
    }


def energy_mass_coefficients(
    config: AnalysisConfig,
    diameter_inch: float,
) -> tuple[float, float]:
    """Return (c, k) in F(m) = m_nb + c + k * m^(3/2) - m."""
    alpha = hover_energy_to_battery_mass_factor(
        config.endurance_s,
        config.pack_specific_energy_wh_kg,
        config.usable_fraction,
    )
    c = avionics_battery_mass_kg(config.avionics_power_w, alpha)
    k = energy_mass_coupling_coefficient(
        config.gravity_m_s2,
        config.air_density_kg_m3,
        inches_to_metres(diameter_inch),
        config.rotor_count,
        config.figure_of_merit,
        config.motor_esc_efficiency,
        alpha,
    )
    return c, k


def solve_battery_feedback(
    config: AnalysisConfig,
    scenario: MassScenario,
    diameter_inch: float,
    uncertainty_case: str = 'nominal',
) -> PropulsionResult:
    """Analytic existence test plus bisection for the smaller physical root.

    Fixed-point iteration is recorded only as a cross-check and is never
    used as the existence proof.
    """
    config.validate()
    if scenario.non_battery_mass_kg <= 0.0:
        raise InvalidInputError(
            f'{scenario.name}.non_battery_mass_kg must be > 0'
        )
    c, k = energy_mass_coefficients(config, diameter_inch)
    m_crit = critical_total_mass_kg(k)
    m_nb_max = maximum_non_battery_mass_for_closure_kg(c, k)
    m_nb = scenario.non_battery_mass_kg
    closure_margin = m_nb_max - m_nb
    f_min = energy_mass_residual_kg(m_crit, m_nb, c, k)
    hover_open = evaluate_hover_at_mass(config, m_nb, diameter_inch)
    diagnostic_power = hover_open['electrical_hover_power_w']
    diagnostic_battery = required_battery_mass_kg(
        diagnostic_power,
        config.endurance_s,
        config.pack_specific_energy_wh_kg,
        config.usable_fraction,
    )
    analytic = {
        'critical_total_mass_kg': m_crit,
        'maximum_non_battery_mass_for_closure_kg': m_nb_max,
        'closure_margin_kg': closure_margin,
        'f_min_kg': f_min,
        'c_kg': c,
        'k': k,
    }
    if f_min > 0.0:
        return _build_result(
            config,
            scenario,
            diameter_inch,
            uncertainty_case=uncertainty_case,
            hover_closed=None,
            battery_mass_kg=None,
            total_mass_kg=None,
            energy_mass_closure=False,
            energy_mass_closure_status=STATUS_ENERGY_MASS_CLOSURE_INFEASIBLE,
            root_method=ROOT_METHOD_NONE,
            root_iterations=0,
            residual_kg=None,
            diagnostic_first_iteration_battery_mass_kg=diagnostic_battery,
            diagnostic_non_battery_mass_power_w=diagnostic_power,
            analytic=analytic,
            extra_flags=(STATUS_ENERGY_MASS_CLOSURE_INFEASIBLE,),
            fixed_point_crosscheck_converged=None,
            fixed_point_crosscheck_total_mass_kg=None,
        )
    total_mass, iterations, residual = _bisect_smaller_energy_mass_root(
        non_battery_mass_kg=m_nb,
        avionics_battery_mass_offset_kg=c,
        coupling_k=k,
        mass_lo_kg=m_nb,
        mass_hi_kg=m_crit,
        tolerance_kg=config.mass_tolerance_kg,
        max_iterations=config.max_iterations,
        scenario_name=scenario.name,
        diameter_inch=diameter_inch,
    )
    if abs(residual) > config.mass_tolerance_kg:
        raise ConvergenceError(
            'bisection residual exceeds tolerance after analytic existence '
            f'for scenario={scenario.name!r} diameter_inch={diameter_inch}: '
            f'residual_kg={residual}'
        )
    hover_closed = evaluate_hover_at_mass(config, total_mass, diameter_inch)
    battery_mass = total_mass - m_nb
    fp_ok, fp_mass = _fixed_point_crosscheck(
        config, scenario, diameter_inch, total_mass
    )
    extra_flags = [STATUS_CONDITIONAL_ENERGY_CLOSURE]
    if fp_ok is False:
        extra_flags.append('FIXED_POINT_CROSSCHECK_MISMATCH')
    return _build_result(
        config,
        scenario,
        diameter_inch,
        uncertainty_case=uncertainty_case,
        hover_closed=hover_closed,
        battery_mass_kg=battery_mass,
        total_mass_kg=total_mass,
        energy_mass_closure=True,
        energy_mass_closure_status=STATUS_CONDITIONAL_ENERGY_CLOSURE,
        root_method=ROOT_METHOD_BISECTION,
        root_iterations=iterations,
        residual_kg=residual,
        diagnostic_first_iteration_battery_mass_kg=diagnostic_battery,
        diagnostic_non_battery_mass_power_w=diagnostic_power,
        analytic=analytic,
        extra_flags=tuple(extra_flags),
        fixed_point_crosscheck_converged=fp_ok,
        fixed_point_crosscheck_total_mass_kg=fp_mass,
    )


def solve_all(
    config: AnalysisConfig,
    uncertainty_case: str = 'nominal',
) -> tuple[PropulsionResult, ...]:
    """Solve every mass scenario against every propeller diameter."""
    config.validate()
    rows = []
    for scenario in config.mass_scenarios:
        for diameter_inch in config.propellers_inch:
            rows.append(
                solve_battery_feedback(
                    config, scenario, diameter_inch, uncertainty_case
                )
            )
    return tuple(rows)


def solve_all_uncertainty_cases(
    config: AnalysisConfig,
) -> dict[str, tuple[PropulsionResult, ...]]:
    """Solve the full matrix under conservative, nominal, and optimistic bounds."""
    config.validate()
    by_case: dict[str, tuple[PropulsionResult, ...]] = {}
    for case in config.uncertainty_cases:
        applied = apply_uncertainty_case(config, case)
        by_case[case.name] = solve_all(applied, uncertainty_case=case.name)
    return by_case


def _bisect_smaller_energy_mass_root(
    non_battery_mass_kg: float,
    avionics_battery_mass_offset_kg: float,
    coupling_k: float,
    mass_lo_kg: float,
    mass_hi_kg: float,
    tolerance_kg: float,
    max_iterations: int,
    scenario_name: str,
    diameter_inch: float,
) -> tuple[float, int, float]:
    """Bisection on [m_nb, m_critical] for the smaller physical root of F."""
    if mass_hi_kg < mass_lo_kg:
        raise ConvergenceError(
            'bisection interval is empty for '
            f'scenario={scenario_name!r} diameter_inch={diameter_inch}'
        )

    def residual(mass_kg: float) -> float:
        return energy_mass_residual_kg(
            mass_kg,
            non_battery_mass_kg,
            avionics_battery_mass_offset_kg,
            coupling_k,
        )

    f_lo = residual(mass_lo_kg)
    f_hi = residual(mass_hi_kg)
    if abs(f_hi) <= tolerance_kg:
        return mass_hi_kg, 0, f_hi
    if abs(f_lo) <= tolerance_kg:
        return mass_lo_kg, 0, f_lo
    if f_lo <= 0.0:
        raise ConvergenceError(
            'F(m_non_battery) is not positive; smaller-root bracket failed for '
            f'scenario={scenario_name!r} diameter_inch={diameter_inch}'
        )
    if f_hi > 0.0:
        raise ConvergenceError(
            'F(m_critical) is positive after the existence test for '
            f'scenario={scenario_name!r} diameter_inch={diameter_inch}'
        )
    lo = mass_lo_kg
    hi = mass_hi_kg
    mid = 0.5 * (lo + hi)
    f_mid = residual(mid)
    for iteration in range(1, max_iterations + 1):
        mid = 0.5 * (lo + hi)
        f_mid = residual(mid)
        if abs(f_mid) <= tolerance_kg:
            return mid, iteration, f_mid
        if f_mid > 0.0:
            lo = mid
        else:
            hi = mid
    if abs(f_mid) <= tolerance_kg:
        return mid, max_iterations, f_mid
    raise ConvergenceError(
        'bisection failed to reduce |F(m)| to tolerance for '
        f'scenario={scenario_name!r} diameter_inch={diameter_inch} '
        f'after {max_iterations} iterations (residual_kg={f_mid})'
    )


def _fixed_point_crosscheck(
    config: AnalysisConfig,
    scenario: MassScenario,
    diameter_inch: float,
    expected_total_mass_kg: float,
) -> tuple[bool | None, float | None]:
    """Optional fixed-point agreement check. Not an existence proof."""
    battery_mass = 0.0
    try:
        for _iteration in range(1, config.max_iterations + 1):
            total_mass = scenario.non_battery_mass_kg + battery_mass
            hover = evaluate_hover_at_mass(config, total_mass, diameter_inch)
            battery_next = required_battery_mass_kg(
                hover['electrical_hover_power_w'],
                config.endurance_s,
                config.pack_specific_energy_wh_kg,
                config.usable_fraction,
            )
            if not math.isfinite(battery_next):
                return False, None
            if abs(battery_next - battery_mass) <= config.mass_tolerance_kg:
                closed = scenario.non_battery_mass_kg + battery_next
                agrees = (
                    abs(closed - expected_total_mass_kg)
                    <= 10.0 * config.mass_tolerance_kg
                )
                return agrees, closed
            battery_mass = battery_next
    except (OverflowError, InvalidInputError):
        return False, None
    return False, None


def _geometry_for_diameter(
    config: AnalysisConfig,
    diameter_m: float,
) -> tuple[float, float, bool, str]:
    current_r = config.current_motor_center_radius_m
    adjacent = adjacent_motor_center_distance_m(current_r, config.rotor_count)
    min_r = min_motor_center_radius_m(
        diameter_m, config.min_tip_clearance_m, config.rotor_count
    )
    required_adjacent = diameter_m + config.min_tip_clearance_m
    fits = min_r <= current_r and adjacent + 1.0e-12 >= required_adjacent
    if fits:
        geometry_conflict = 'none'
    else:
        geometry_conflict = (
            f'G1 hex_arm_span={current_r:.3f} m cannot host D={diameter_m:.4f} m '
            f'with tip gap {config.min_tip_clearance_m:.3f} m '
            f'(needs R>={min_r:.4f} m; URDF was not modified)'
        )
    return adjacent, min_r, fits, geometry_conflict


def _combined_gate(geometry_fit: bool, energy_closed: bool) -> str:
    if geometry_fit and energy_closed:
        return GATE_CONDITIONAL_CANDIDATE
    return GATE_REJECTED_FOR_CURRENT_BASELINE


def _build_result(
    config: AnalysisConfig,
    scenario: MassScenario,
    diameter_inch: float,
    uncertainty_case: str,
    hover_closed: Mapping[str, float] | None,
    battery_mass_kg: float | None,
    total_mass_kg: float | None,
    energy_mass_closure: bool,
    energy_mass_closure_status: str,
    root_method: str,
    root_iterations: int,
    residual_kg: float | None,
    diagnostic_first_iteration_battery_mass_kg: float,
    diagnostic_non_battery_mass_power_w: float,
    analytic: Mapping[str, float],
    extra_flags: tuple[str, ...],
    fixed_point_crosscheck_converged: bool | None,
    fixed_point_crosscheck_total_mass_kg: float | None,
) -> PropulsionResult:
    diameter_m = inches_to_metres(diameter_inch)
    adjacent, min_r, fits, geometry_conflict = _geometry_for_diameter(
        config, diameter_m
    )
    current_r = config.current_motor_center_radius_m
    area_one = rotor_disk_area_m2(diameter_m)
    area_total = total_rotor_disk_area_m2(diameter_m, config.rotor_count)
    gate = _combined_gate(fits, energy_mass_closure)
    battery_fraction = None
    if (
        battery_mass_kg is not None
        and total_mass_kg is not None
        and total_mass_kg > 0.0
    ):
        battery_fraction = battery_mass_kg / total_mass_kg
    n1_burden = n1_burden_increase_fraction(config.rotor_count)
    if hover_closed is None:
        hover_thrust = None
        hover_thrust_kgf = None
        hover_thrust_motor = None
        hover_thrust_motor_kgf = None
        required_thrust_motor = None
        required_thrust_motor_kgf = None
        disk_n = None
        disk_kg = None
        ideal_power = None
        ideal_power_motor = None
        electrical_power = None
        bus_current = None
        n1_hover = None
        n1_hover_kgf = None
        n1_required = None
        n1_required_kgf = None
    else:
        hover_thrust = hover_closed['hover_thrust_n']
        hover_thrust_kgf = hover_closed['hover_thrust_kgf']
        hover_thrust_motor = hover_closed['hover_thrust_per_motor_n']
        hover_thrust_motor_kgf = hover_closed['hover_thrust_per_motor_kgf']
        required_thrust_motor = hover_closed[
            'required_thrust_per_motor_at_target_tw_n'
        ]
        required_thrust_motor_kgf = hover_closed[
            'required_thrust_per_motor_at_target_tw_kgf'
        ]
        disk_n = hover_closed['disk_loading_n_m2']
        disk_kg = hover_closed['disk_loading_kg_m2']
        ideal_power = hover_closed['ideal_induced_power_w']
        ideal_power_motor = hover_closed['ideal_induced_power_per_motor_w']
        electrical_power = hover_closed['electrical_hover_power_w']
        bus_current = hover_closed['battery_bus_current_a']
        n1_hover = n1_hover_thrust_per_remaining_motor_n(
            hover_thrust, config.rotor_count
        )
        n1_hover_kgf = newtons_to_kgf(n1_hover, config.gravity_m_s2)
        n1_required = n1_required_thrust_per_remaining_motor_at_target_tw_n(
            total_mass_kg,
            config.gravity_m_s2,
            config.rotor_count,
            config.thrust_to_weight_target,
        )
        n1_required_kgf = newtons_to_kgf(n1_required, config.gravity_m_s2)
    flags: list[str] = [
        STATUS_ANALYSIS_ONLY,
        STATUS_NOT_FOR_PROCUREMENT,
        STATUS_OVERALL_UNDETERMINED,
        N1_STATIC_FLAG,
        gate,
    ]
    flags.extend(extra_flags)
    if not fits:
        flags.append('GEOMETRY_CONFLICT_G1_ARM_SPAN')
    if (
        battery_fraction is not None
        and math.isfinite(battery_fraction)
        and battery_fraction >= config.battery_mass_fraction_warn
    ):
        flags.append('BATTERY_MASS_FRACTION_HIGH')
    if disk_n is not None and disk_n >= config.disk_loading_n_m2_warn:
        flags.append('DISK_LOADING_HIGH')
    flags.append('ENERGY_CLOSURE_EXCLUDES_UNMODELED_HARDWARE_MASS')
    return PropulsionResult(
        status=STATUS_ANALYSIS_ONLY,
        procurement_allowed=False,
        overall_propulsion_feasibility=STATUS_OVERALL_UNDETERMINED,
        uncertainty_case=uncertainty_case,
        scenario_name=scenario.name,
        scenario_description=scenario.description,
        diameter_inch=float(diameter_inch),
        diameter_m=diameter_m,
        non_battery_mass_kg=scenario.non_battery_mass_kg,
        battery_mass_kg=battery_mass_kg,
        total_mass_kg=total_mass_kg,
        rotor_count=config.rotor_count,
        area_one_m2=area_one,
        area_total_m2=area_total,
        hover_thrust_n=hover_thrust,
        hover_thrust_kgf=hover_thrust_kgf,
        hover_thrust_per_motor_n=hover_thrust_motor,
        hover_thrust_per_motor_kgf=hover_thrust_motor_kgf,
        required_thrust_per_motor_at_target_tw_n=required_thrust_motor,
        required_thrust_per_motor_at_target_tw_kgf=required_thrust_motor_kgf,
        disk_loading_n_m2=disk_n,
        disk_loading_kg_m2=disk_kg,
        ideal_induced_power_w=ideal_power,
        ideal_induced_power_per_motor_w=ideal_power_motor,
        electrical_hover_power_w=electrical_power,
        battery_bus_current_a=bus_current,
        battery_bus_current_note=_BUS_CURRENT_NOTE,
        adjacent_motor_center_m=adjacent,
        min_motor_center_radius_m=min_r,
        rotor_envelope_diameter_at_current_r_m=rotor_envelope_diameter_m(
            current_r, diameter_m
        ),
        rotor_envelope_diameter_at_min_r_m=rotor_envelope_diameter_m(
            min_r, diameter_m
        ),
        current_motor_center_radius_m=current_r,
        current_geometry_fit=fits,
        geometry_conflict=geometry_conflict,
        battery_mass_fraction=battery_fraction,
        energy_mass_closure=energy_mass_closure,
        energy_mass_closure_status=energy_mass_closure_status,
        critical_total_mass_kg=analytic['critical_total_mass_kg'],
        maximum_non_battery_mass_for_closure_kg=analytic[
            'maximum_non_battery_mass_for_closure_kg'
        ],
        closure_margin_kg=analytic['closure_margin_kg'],
        root_method=root_method,
        root_iterations=root_iterations,
        residual_kg=residual_kg,
        diagnostic_first_iteration_battery_mass_kg=(
            diagnostic_first_iteration_battery_mass_kg
        ),
        diagnostic_non_battery_mass_power_w=diagnostic_non_battery_mass_power_w,
        combined_current_baseline_gate=gate,
        n1_hover_thrust_per_remaining_motor_n=n1_hover,
        n1_hover_thrust_per_remaining_motor_kgf=n1_hover_kgf,
        n1_burden_increase_fraction=n1_burden,
        n1_required_thrust_per_remaining_motor_at_target_tw_n=n1_required,
        n1_required_thrust_per_remaining_motor_at_target_tw_kgf=n1_required_kgf,
        n1_interpretation=N1_STATIC_FLAG,
        fixed_point_crosscheck_converged=fixed_point_crosscheck_converged,
        fixed_point_crosscheck_total_mass_kg=fixed_point_crosscheck_total_mass_kg,
        missing_closed_vehicle_mass_items=MISSING_CLOSED_VEHICLE_MASS_ITEMS,
        risk_flags=tuple(flags),
    )
