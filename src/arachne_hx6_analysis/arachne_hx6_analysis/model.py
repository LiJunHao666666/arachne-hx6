"""SI propulsion geometry and momentum-theory helpers.

All numeric modeling assumptions belong in YAML, not in this module.
Defined conversion constants are exact unit definitions, not vehicle data.

ANALYSIS_ONLY. NOT_FOR_PROCUREMENT.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Mapping

INCH_TO_METRE = 0.0254
SECONDS_PER_HOUR = 3600.0
STATUS_ANALYSIS_ONLY = 'ANALYSIS_ONLY'
STATUS_NOT_FOR_PROCUREMENT = 'NOT_FOR_PROCUREMENT'
STATUS_ENERGY_MASS_CLOSURE_INFEASIBLE = 'ENERGY_MASS_CLOSURE_INFEASIBLE'
STATUS_CONDITIONAL_ENERGY_CLOSURE = 'CONDITIONAL_ENERGY_CLOSURE'
STATUS_OVERALL_UNDETERMINED = 'UNDETERMINED'
GATE_CONDITIONAL_CANDIDATE = 'CONDITIONAL_CANDIDATE'
GATE_REJECTED_FOR_CURRENT_BASELINE = 'REJECTED_FOR_CURRENT_BASELINE'
N1_STATIC_FLAG = 'STATIC_THRUST_ONLY_NOT_CONTROL_AUTHORITY_PROOF'
ROOT_METHOD_BISECTION = 'bisection'
ROOT_METHOD_NONE = 'none'
ROOT_METHOD_FIXED_POINT_CROSSCHECK = 'fixed_point_crosscheck'
REQUIRED_UNCERTAINTY_CASES = ('conservative', 'nominal', 'optimistic')
MISSING_CLOSED_VEHICLE_MASS_ITEMS = (
    'real motor mass',
    'ESC mass',
    'propeller and hub mass',
    'extended arm and fastener mass',
    'high-current harness, connector, and protection mass',
    'structural reinforcement mass',
    'thermal / cooling mass',
    'protective structure mass',
)


class AnalysisError(ValueError):
    """Base error for G1.5 propulsion analysis."""


class InvalidInputError(AnalysisError):
    """Raised when a planning input is non-physical or out of range."""


class ConvergenceError(AnalysisError):
    """Raised when a numerically required root cannot be refined to tolerance.

    Analytic non-existence of energy-mass closure is not a ConvergenceError.
    """


def inches_to_metres(diameter_inch: float) -> float:
    """Convert a propeller diameter from inches to metres."""
    _require_positive(diameter_inch, 'diameter_inch')
    return diameter_inch * INCH_TO_METRE


def rotor_disk_area_m2(diameter_m: float) -> float:
    """Single-rotor actuator-disk area A = pi * (D/2)^2."""
    _require_positive(diameter_m, 'diameter_m')
    radius_m = diameter_m / 2.0
    return math.pi * radius_m * radius_m


def total_rotor_disk_area_m2(diameter_m: float, rotor_count: int) -> float:
    """Sum of n identical rotor disks."""
    _require_rotor_count(rotor_count)
    return float(rotor_count) * rotor_disk_area_m2(diameter_m)


def hover_thrust_n(total_mass_kg: float, gravity_m_s2: float) -> float:
    """Total hover thrust T = m g."""
    _require_positive(total_mass_kg, 'total_mass_kg')
    _require_positive(gravity_m_s2, 'gravity_m_s2')
    return total_mass_kg * gravity_m_s2


def hover_thrust_per_motor_n(
    total_mass_kg: float,
    gravity_m_s2: float,
    rotor_count: int,
) -> float:
    """Equal hover-thrust split T / n."""
    _require_rotor_count(rotor_count)
    return hover_thrust_n(total_mass_kg, gravity_m_s2) / float(rotor_count)


def max_thrust_per_motor_n(
    total_mass_kg: float,
    gravity_m_s2: float,
    rotor_count: int,
    thrust_to_weight_target: float,
) -> float:
    """Per-motor thrust at a planning thrust-to-weight target."""
    _require_positive(thrust_to_weight_target, 'thrust_to_weight_target')
    _require_rotor_count(rotor_count)
    return (
        thrust_to_weight_target
        * hover_thrust_n(total_mass_kg, gravity_m_s2)
        / float(rotor_count)
    )


def disk_loading_n_m2(thrust_n: float, area_m2: float) -> float:
    """Disk loading in N/m^2."""
    _require_non_negative(thrust_n, 'thrust_n')
    _require_positive(area_m2, 'area_m2')
    return thrust_n / area_m2


def disk_loading_kg_m2(mass_kg: float, area_m2: float) -> float:
    """Disk loading in kg/m^2, equal to (T/A)/g for hover."""
    _require_positive(mass_kg, 'mass_kg')
    _require_positive(area_m2, 'area_m2')
    return mass_kg / area_m2


def ideal_induced_power_w(
    thrust_n: float,
    area_m2: float,
    air_density_kg_m3: float,
) -> float:
    """Ideal hover induced power P = T^(3/2) / sqrt(2 rho A)."""
    _require_non_negative(thrust_n, 'thrust_n')
    _require_positive(area_m2, 'area_m2')
    _require_positive(air_density_kg_m3, 'air_density_kg_m3')
    return (thrust_n ** 1.5) / math.sqrt(2.0 * air_density_kg_m3 * area_m2)


def total_ideal_induced_power_w(
    total_thrust_n: float,
    diameter_m: float,
    rotor_count: int,
    air_density_kg_m3: float,
) -> float:
    """Sum of n identical ideal induced powers."""
    _require_rotor_count(rotor_count)
    thrust_one = total_thrust_n / float(rotor_count)
    area_one = rotor_disk_area_m2(diameter_m)
    return float(rotor_count) * ideal_induced_power_w(
        thrust_one, area_one, air_density_kg_m3
    )


def electrical_hover_power_w(
    ideal_power_w: float,
    figure_of_merit: float,
    motor_esc_efficiency: float,
    avionics_power_w: float,
) -> float:
    """P_elec = P_ideal / (FoM * eta_motor_esc) + P_avionics."""
    _require_non_negative(ideal_power_w, 'ideal_power_w')
    _require_unit_interval_exclusive_zero(figure_of_merit, 'figure_of_merit')
    _require_unit_interval_exclusive_zero(
        motor_esc_efficiency, 'motor_esc_efficiency'
    )
    _require_non_negative(avionics_power_w, 'avionics_power_w')
    return ideal_power_w / (figure_of_merit * motor_esc_efficiency) + avionics_power_w


def battery_bus_current_a(electrical_power_w: float, bus_voltage_v: float) -> float:
    """Total DC input current at the planning nominal battery-bus voltage.

    I_bus = P_elec / V_bus_nominal. This is not a per-motor phase current
    and does not model voltage sag, wiring loss, or peak current.
    """
    _require_non_negative(electrical_power_w, 'electrical_power_w')
    _require_positive(bus_voltage_v, 'bus_voltage_v')
    return electrical_power_w / bus_voltage_v


def newtons_to_kgf(force_n: float, gravity_m_s2: float) -> float:
    """Convert newtons to kilogram-force using the same planning g."""
    _require_non_negative(force_n, 'force_n')
    _require_positive(gravity_m_s2, 'gravity_m_s2')
    return force_n / gravity_m_s2


def hover_energy_to_battery_mass_factor(
    endurance_s: float,
    pack_specific_energy_wh_kg: float,
    usable_fraction: float,
) -> float:
    """alpha such that m_batt = alpha * P_elec, with P_elec in watts."""
    _require_positive(endurance_s, 'endurance_s')
    _require_positive(pack_specific_energy_wh_kg, 'pack_specific_energy_wh_kg')
    _require_unit_interval_exclusive_zero(usable_fraction, 'usable_fraction')
    return endurance_s / (
        SECONDS_PER_HOUR * pack_specific_energy_wh_kg * usable_fraction
    )


def avionics_battery_mass_kg(
    avionics_power_w: float,
    energy_to_mass_factor: float,
) -> float:
    """c: battery mass attributed to constant avionics power."""
    _require_non_negative(avionics_power_w, 'avionics_power_w')
    _require_positive(energy_to_mass_factor, 'energy_to_mass_factor')
    return energy_to_mass_factor * avionics_power_w


def energy_mass_coupling_coefficient(
    gravity_m_s2: float,
    air_density_kg_m3: float,
    diameter_m: float,
    rotor_count: int,
    figure_of_merit: float,
    motor_esc_efficiency: float,
    energy_to_mass_factor: float,
) -> float:
    """k such that rotor-related battery mass = k * m^(3/2)."""
    _require_positive(gravity_m_s2, 'gravity_m_s2')
    _require_positive(air_density_kg_m3, 'air_density_kg_m3')
    _require_rotor_count(rotor_count)
    _require_unit_interval_exclusive_zero(figure_of_merit, 'figure_of_merit')
    _require_unit_interval_exclusive_zero(
        motor_esc_efficiency, 'motor_esc_efficiency'
    )
    _require_positive(energy_to_mass_factor, 'energy_to_mass_factor')
    area_one = rotor_disk_area_m2(diameter_m)
    denom = (
        figure_of_merit
        * motor_esc_efficiency
        * math.sqrt(
            2.0 * float(rotor_count) * air_density_kg_m3 * area_one
        )
    )
    return energy_to_mass_factor * (gravity_m_s2 ** 1.5) / denom


def energy_mass_residual_kg(
    total_mass_kg: float,
    non_battery_mass_kg: float,
    avionics_battery_mass_offset_kg: float,
    coupling_k: float,
) -> float:
    """F(m) = m_non_battery + c + k * m^(3/2) - m."""
    _require_positive(total_mass_kg, 'total_mass_kg')
    _require_positive(non_battery_mass_kg, 'non_battery_mass_kg')
    _require_non_negative(
        avionics_battery_mass_offset_kg, 'avionics_battery_mass_offset_kg'
    )
    _require_positive(coupling_k, 'coupling_k')
    return (
        non_battery_mass_kg
        + avionics_battery_mass_offset_kg
        + coupling_k * (total_mass_kg ** 1.5)
        - total_mass_kg
    )


def critical_total_mass_kg(coupling_k: float) -> float:
    """Location of F'(m)=0: m_critical = (2 / (3 k))^2."""
    _require_positive(coupling_k, 'coupling_k')
    return (2.0 / (3.0 * coupling_k)) ** 2


def maximum_non_battery_mass_for_closure_kg(
    avionics_battery_mass_offset_kg: float,
    coupling_k: float,
) -> float:
    """Largest m_non_battery for which min F(m) <= 0."""
    _require_non_negative(
        avionics_battery_mass_offset_kg, 'avionics_battery_mass_offset_kg'
    )
    m_crit = critical_total_mass_kg(coupling_k)
    return (
        m_crit
        - avionics_battery_mass_offset_kg
        - coupling_k * (m_crit ** 1.5)
    )


def n1_remaining_rotor_count(rotor_count: int) -> int:
    """Motors remaining after one static outage."""
    _require_rotor_count(rotor_count)
    remaining = rotor_count - 1
    if remaining < 1:
        raise InvalidInputError(
            f'N-1 static split requires rotor_count >= 2, got {rotor_count}'
        )
    return remaining


def n1_burden_increase_fraction(rotor_count: int) -> float:
    """(n/(n-1)) - 1. For a hexarotor this is exactly 0.20."""
    remaining = n1_remaining_rotor_count(rotor_count)
    return float(rotor_count) / float(remaining) - 1.0


def n1_hover_thrust_per_remaining_motor_n(
    total_hover_thrust_n: float,
    rotor_count: int,
) -> float:
    """Equal static split of hover thrust across n-1 remaining motors."""
    _require_positive(total_hover_thrust_n, 'total_hover_thrust_n')
    remaining = n1_remaining_rotor_count(rotor_count)
    return total_hover_thrust_n / float(remaining)


def n1_max_thrust_per_remaining_motor_n(
    total_mass_kg: float,
    gravity_m_s2: float,
    rotor_count: int,
    thrust_to_weight_target: float,
) -> float:
    """Per-remaining-motor thrust at the planning thrust-to-weight target."""
    _require_positive(thrust_to_weight_target, 'thrust_to_weight_target')
    remaining = n1_remaining_rotor_count(rotor_count)
    return (
        thrust_to_weight_target
        * hover_thrust_n(total_mass_kg, gravity_m_s2)
        / float(remaining)
    )


def required_battery_mass_kg(
    electrical_power_w: float,
    endurance_s: float,
    pack_specific_energy_wh_kg: float,
    usable_fraction: float,
) -> float:
    """Battery mass from hover energy, usable fraction, and pack energy."""
    _require_non_negative(electrical_power_w, 'electrical_power_w')
    _require_positive(endurance_s, 'endurance_s')
    _require_positive(pack_specific_energy_wh_kg, 'pack_specific_energy_wh_kg')
    _require_unit_interval_exclusive_zero(usable_fraction, 'usable_fraction')
    energy_wh = electrical_power_w * endurance_s / SECONDS_PER_HOUR
    return energy_wh / (pack_specific_energy_wh_kg * usable_fraction)


def adjacent_motor_center_distance_m(
    motor_center_radius_m: float,
    rotor_count: int,
) -> float:
    """Chord between adjacent motors on a regular n-gon: 2 R sin(pi/n)."""
    _require_positive(motor_center_radius_m, 'motor_center_radius_m')
    _require_rotor_count(rotor_count)
    return 2.0 * motor_center_radius_m * math.sin(math.pi / float(rotor_count))


def min_motor_center_radius_m(
    diameter_m: float,
    min_tip_clearance_m: float,
    rotor_count: int,
) -> float:
    """Smallest R such that adjacent disks keep the planning tip gap."""
    _require_positive(diameter_m, 'diameter_m')
    _require_non_negative(min_tip_clearance_m, 'min_tip_clearance_m')
    _require_rotor_count(rotor_count)
    required_adjacent = diameter_m + min_tip_clearance_m
    return required_adjacent / (2.0 * math.sin(math.pi / float(rotor_count)))


def rotor_envelope_diameter_m(
    motor_center_radius_m: float,
    diameter_m: float,
) -> float:
    """Circumscribed diameter of the six-disk layout: 2R + D."""
    _require_positive(motor_center_radius_m, 'motor_center_radius_m')
    _require_positive(diameter_m, 'diameter_m')
    return 2.0 * motor_center_radius_m + diameter_m


def _require_positive(value: float, name: str) -> None:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise InvalidInputError(f'{name} must be a real number, got {value!r}')
    if not math.isfinite(value) or value <= 0.0:
        raise InvalidInputError(f'{name} must be finite and > 0, got {value}')


def _require_non_negative(value: float, name: str) -> None:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise InvalidInputError(f'{name} must be a real number, got {value!r}')
    if not math.isfinite(value) or value < 0.0:
        raise InvalidInputError(f'{name} must be finite and >= 0, got {value}')


def _require_unit_interval_exclusive_zero(value: float, name: str) -> None:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise InvalidInputError(f'{name} must be a real number, got {value!r}')
    if not math.isfinite(value) or value <= 0.0 or value > 1.0:
        raise InvalidInputError(
            f'{name} must be in (0, 1], got {value}'
        )


def _require_rotor_count(rotor_count: int) -> None:
    if not isinstance(rotor_count, int) or isinstance(rotor_count, bool):
        raise InvalidInputError(
            f'rotor_count must be an integer, got {rotor_count!r}'
        )
    if rotor_count < 2:
        raise InvalidInputError(
            f'rotor_count must be an integer >= 2, got {rotor_count}'
        )


@dataclass(frozen=True)
class MassScenario:
    """Named non-battery mass case. Planning input only."""

    name: str
    non_battery_mass_kg: float
    description: str


@dataclass(frozen=True)
class UncertaintyCase:
    """Named planning bound set. Not measured vehicle data."""

    name: str
    air_density_kg_m3: float
    figure_of_merit: float
    motor_esc_efficiency: float
    pack_specific_energy_wh_kg: float
    usable_fraction: float
    avionics_power_w: float
    description: str


@dataclass(frozen=True)
class AnalysisConfig:
    """Loaded YAML planning inputs. Not hardware calibration."""

    status: str
    procurement_allowed: bool
    notes: str
    gravity_m_s2: float
    air_density_kg_m3: float
    rotor_count: int
    thrust_to_weight_target: float
    figure_of_merit: float
    motor_esc_efficiency: float
    bus_voltage_v: float
    avionics_power_w: float
    usable_fraction: float
    pack_specific_energy_wh_kg: float
    endurance_s: float
    mass_tolerance_kg: float
    max_iterations: int
    current_motor_center_radius_m: float
    min_tip_clearance_m: float
    battery_mass_fraction_warn: float
    disk_loading_n_m2_warn: float
    propellers_inch: tuple[float, ...]
    mass_scenarios: tuple[MassScenario, ...]
    uncertainty_cases: tuple[UncertaintyCase, ...]
    raw: Mapping[str, object] = field(repr=False)

    def validate(self) -> None:
        """Reject non-physical planning inputs before any solve."""
        if self.status != STATUS_ANALYSIS_ONLY:
            raise InvalidInputError(
                f'status must be {STATUS_ANALYSIS_ONLY}, got {self.status!r}'
            )
        if self.procurement_allowed:
            raise InvalidInputError('procurement_allowed must be false')
        _require_positive(self.gravity_m_s2, 'gravity_m_s2')
        _require_positive(self.air_density_kg_m3, 'air_density_kg_m3')
        _require_rotor_count(self.rotor_count)
        _require_positive(self.thrust_to_weight_target, 'thrust_to_weight_target')
        _require_unit_interval_exclusive_zero(self.figure_of_merit, 'figure_of_merit')
        _require_unit_interval_exclusive_zero(
            self.motor_esc_efficiency, 'motor_esc_efficiency'
        )
        _require_positive(self.bus_voltage_v, 'bus_voltage_v')
        _require_non_negative(self.avionics_power_w, 'avionics_power_w')
        _require_unit_interval_exclusive_zero(self.usable_fraction, 'usable_fraction')
        _require_positive(
            self.pack_specific_energy_wh_kg, 'pack_specific_energy_wh_kg'
        )
        _require_positive(self.endurance_s, 'endurance_s')
        _require_positive(self.mass_tolerance_kg, 'mass_tolerance_kg')
        if not isinstance(self.max_iterations, int) or self.max_iterations < 1:
            raise InvalidInputError(
                f'max_iterations must be an integer >= 1, got {self.max_iterations}'
            )
        _require_positive(
            self.current_motor_center_radius_m, 'current_motor_center_radius_m'
        )
        _require_non_negative(self.min_tip_clearance_m, 'min_tip_clearance_m')
        _require_unit_interval_exclusive_zero(
            self.battery_mass_fraction_warn, 'battery_mass_fraction_warn'
        )
        _require_positive(self.disk_loading_n_m2_warn, 'disk_loading_n_m2_warn')
        if not self.propellers_inch:
            raise InvalidInputError('propellers_inch must not be empty')
        for diameter_inch in self.propellers_inch:
            _require_positive(diameter_inch, 'propellers_inch item')
        if not self.mass_scenarios:
            raise InvalidInputError('mass_scenarios must not be empty')
        for scenario in self.mass_scenarios:
            if not scenario.name:
                raise InvalidInputError('mass scenario name must be non-empty')
            _require_positive(
                scenario.non_battery_mass_kg,
                f'{scenario.name}.non_battery_mass_kg',
            )
        self._validate_uncertainty_cases()

    def _validate_uncertainty_cases(self) -> None:
        names = tuple(case.name for case in self.uncertainty_cases)
        missing = [
            name for name in REQUIRED_UNCERTAINTY_CASES if name not in names
        ]
        if missing:
            raise InvalidInputError(
                'uncertainty_cases must include conservative, nominal, and '
                f'optimistic; missing {missing}'
            )
        seen: set[str] = set()
        for case in self.uncertainty_cases:
            if case.name in seen:
                raise InvalidInputError(
                    f'duplicate uncertainty case name: {case.name!r}'
                )
            seen.add(case.name)
            if not case.name:
                raise InvalidInputError('uncertainty case name must be non-empty')
            _require_positive(
                case.air_density_kg_m3,
                f'{case.name}.air_density_kg_m3',
            )
            _require_unit_interval_exclusive_zero(
                case.figure_of_merit, f'{case.name}.figure_of_merit'
            )
            _require_unit_interval_exclusive_zero(
                case.motor_esc_efficiency,
                f'{case.name}.motor_esc_efficiency',
            )
            _require_positive(
                case.pack_specific_energy_wh_kg,
                f'{case.name}.pack_specific_energy_wh_kg',
            )
            _require_unit_interval_exclusive_zero(
                case.usable_fraction, f'{case.name}.usable_fraction'
            )
            _require_non_negative(
                case.avionics_power_w, f'{case.name}.avionics_power_w'
            )
