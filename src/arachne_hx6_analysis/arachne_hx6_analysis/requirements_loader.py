"""Load and strictly validate the four official G3 YAML contracts.

ANALYSIS_ONLY. NOT_FOR_PROCUREMENT.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from arachne_hx6_analysis.architecture_types import REQUIRED_MASS_LEDGER_ITEMS
from arachne_hx6_analysis.evidence_ledger import (
    reject_claimed_high_level_without_quantitative_content,
    validate_evidence_level_metadata,
)
from arachne_hx6_analysis.inputs import (
    as_bool,
    as_list,
    as_mapping,
    as_optional_float,
    as_str,
    require_key,
)
from arachne_hx6_analysis.model import InvalidInputError
from arachne_hx6_analysis.requirements_types import (
    ALLOWED_CATEGORIES,
    ALLOWED_COMBINATION_METHODS,
    ALLOWED_COMPONENT_IDS,
    ALLOWED_EVIDENCE_LEVELS,
    ALLOWED_REQUIREMENT_KINDS,
    ALLOWED_VERIFICATION_METHODS,
    COMPONENT_INCOMPLETE,
    EVIDENCE_MISSING,
    KIND_QUANTITATIVE,
    REQUIRED_UNCERTAINTY_SOURCES,
    REQUIREMENT_INCOMPLETE,
    REQUIREMENT_SPECIFIED,
    TEST_NOT_PERFORMED,
    ArmCouplingContract,
    EvidenceRecord,
    MassComponent,
    RequirementRecord,
    RequirementsConfig,
    StowContract,
    TestRecord,
    UncertaintySource,
)
from arachne_hx6_analysis.requirements_validation import (
    as_allowed_str,
    as_id_list,
    as_nonempty_id,
    as_optional_int,
    as_optional_non_negative_float,
    as_optional_nonempty_str,
    as_optional_str,
    as_positive_int,
    load_yaml_mapping,
    reject_unknown_keys,
    require_analysis_only_header,
    require_interval,
    require_unique_ids,
    require_unit_when_numeric,
)

_REQ_KEYS = (
    'requirement_id',
    'title',
    'category',
    'description',
    'rationale',
    'verification_method',
    'required_evidence_ids',
    'linked_test_ids',
    'linked_report_fields',
    'threshold',
    'value',
    'range_lower',
    'range_upper',
    'unit',
    'applicability',
    'blocking',
    'notes',
    'kind',
)
_TEST_KEYS = (
    'test_id',
    'title',
    'method',
    'linked_requirement_ids',
    'status',
    'notes',
)
_EVIDENCE_KEYS = (
    'evidence_id',
    'component_id',
    'parameter',
    'evidence_level',
    'value',
    'lower',
    'upper',
    'unit',
    'source',
    'source_date',
    'measurement_method',
    'sample_count',
    'uncertainty',
    'linked_requirement_ids',
    'status',
    'notes',
    'vendor',
    'model',
    'access_date',
    'measurement_equipment',
    'measurement_time',
    'test_id',
    'test_conditions',
    'raw_result',
    'verdict',
    'uncertainty_unit',
)
_MASS_KEYS = (
    'component_id',
    'quantity',
    'mass_lower_kg',
    'mass_upper_kg',
    'evidence_id',
    'notes',
)
_UNCERT_KEYS = (
    'source_id',
    'lower_m',
    'upper_m',
    'allowance_m',
    'unit',
    'evidence_id',
    'notes',
)
_ARM_KEYS = (
    'baseline_radius_m',
    'candidate_radius_m',
    'extension_length_per_arm_m',
    'arm_count',
    'linear_mass_lower_kg_per_m',
    'linear_mass_upper_kg_per_m',
    'connector_mass_lower_kg',
    'connector_mass_upper_kg',
    'wiring_mass_lower_kg_per_m',
    'wiring_mass_upper_kg_per_m',
    'reinforcement_mass_lower_kg',
    'reinforcement_mass_upper_kg',
    'evidence_ids',
    'notes',
)
_STOW_VALUE_KEYS = (
    'maximum_stowed_length_m',
    'maximum_stowed_width_m',
    'maximum_stowed_height_m',
    'minimum_rotor_to_leg_clearance_m',
    'maximum_transition_time_s',
    'actuator_torque_lower_nm',
    'actuator_torque_upper_nm',
    'lock_load_capacity_n',
    'lock_stiffness_nm_per_rad',
    'position_repeatability_rad',
    'power_loss_safe_state',
    'landing_deployment_condition',
    'flight_lock_verification_method',
    'emergency_recovery_requirement',
)
_REQ_ROOT_KEYS = (
    'status',
    'procurement_allowed',
    'notes',
    'requirements',
    'tests',
)
_EVIDENCE_ROOT_KEYS = (
    'status',
    'procurement_allowed',
    'notes',
    'evidence',
    'mass_components',
)
_UNCERT_ROOT_KEYS = (
    'status',
    'procurement_allowed',
    'notes',
    'combination_method',
    'nominal_clearance_margin_m',
    'sources',
    'arm_radius_mass_coupling',
)
_STOW_ROOT_KEYS = (
    'status',
    'procurement_allowed',
    'notes',
) + _STOW_VALUE_KEYS


def default_share_config(name: str) -> Path:
    """Installed share config, then source-tree fallback."""
    try:
        from ament_index_python.packages import get_package_share_directory
        candidate = (
            Path(get_package_share_directory('arachne_hx6_analysis'))
            / 'config'
            / name
        )
        if candidate.is_file():
            return candidate
    except Exception:
        pass
    return Path(__file__).resolve().parent.parent / 'config' / name


def default_config_paths() -> dict[str, Path]:
    """Official production YAML paths."""
    return {
        'requirements': default_share_config('system_requirements.yaml'),
        'evidence': default_share_config('evidence_ledger.yaml'),
        'uncertainty': default_share_config('geometry_uncertainty_budget.yaml'),
        'stow': default_share_config('stow_requirements.yaml'),
    }


def load_requirements_config(
    requirements_path: str | Path | None = None,
    evidence_path: str | Path | None = None,
    uncertainty_path: str | Path | None = None,
    stow_path: str | Path | None = None,
) -> RequirementsConfig:
    """Parse the four G3 YAML files into a validated config."""
    defaults = default_config_paths()
    req_path = Path(requirements_path or defaults['requirements'])
    ev_path = Path(evidence_path or defaults['evidence'])
    un_path = Path(uncertainty_path or defaults['uncertainty'])
    st_path = Path(stow_path or defaults['stow'])
    req_root = load_yaml_mapping(req_path, 'system_requirements')
    ev_root = load_yaml_mapping(ev_path, 'evidence_ledger')
    un_root = load_yaml_mapping(un_path, 'geometry_uncertainty_budget')
    st_root = load_yaml_mapping(st_path, 'stow_requirements')
    reject_unknown_keys(req_root, _REQ_ROOT_KEYS, 'system_requirements')
    reject_unknown_keys(ev_root, _EVIDENCE_ROOT_KEYS, 'evidence_ledger')
    reject_unknown_keys(un_root, _UNCERT_ROOT_KEYS, 'geometry_uncertainty_budget')
    reject_unknown_keys(st_root, _STOW_ROOT_KEYS, 'stow_requirements')
    require_analysis_only_header(req_root, 'system_requirements')
    require_analysis_only_header(ev_root, 'evidence_ledger')
    require_analysis_only_header(un_root, 'geometry_uncertainty_budget')
    require_analysis_only_header(st_root, 'stow_requirements')
    requirements = _parse_requirements(
        as_list(
            require_key(req_root, 'requirements', 'system_requirements'),
            'system_requirements.requirements',
        )
    )
    tests = _parse_tests(
        as_list(
            require_key(req_root, 'tests', 'system_requirements'),
            'system_requirements.tests',
        )
    )
    evidence = _parse_evidence(
        as_list(
            require_key(ev_root, 'evidence', 'evidence_ledger'),
            'evidence_ledger.evidence',
        )
    )
    mass_components = _parse_mass_components(
        as_list(
            require_key(ev_root, 'mass_components', 'evidence_ledger'),
            'evidence_ledger.mass_components',
        )
    )
    sources = _parse_uncertainty_sources(
        as_list(
            require_key(un_root, 'sources', 'geometry_uncertainty_budget'),
            'geometry_uncertainty_budget.sources',
        )
    )
    combination = as_optional_nonempty_str(
        un_root.get('combination_method', None),
        'geometry_uncertainty_budget.combination_method',
    )
    if combination is not None and combination not in ALLOWED_COMBINATION_METHODS:
        raise InvalidInputError(
            'geometry_uncertainty_budget.combination_method must be one of '
            f'{list(ALLOWED_COMBINATION_METHODS)}, got {combination!r}'
        )
    arm = _parse_arm_coupling(
        as_mapping(
            require_key(
                un_root,
                'arm_radius_mass_coupling',
                'geometry_uncertainty_budget',
            ),
            'geometry_uncertainty_budget.arm_radius_mass_coupling',
        )
    )
    stow = _parse_stow(st_root)
    _cross_check_ids(requirements, tests, evidence, mass_components, sources, arm)
    return RequirementsConfig(
        status='ANALYSIS_ONLY',
        procurement_allowed=False,
        notes=as_str(
            require_key(req_root, 'notes', 'system_requirements'),
            'system_requirements.notes',
        ),
        requirements=requirements,
        tests=tests,
        evidence=evidence,
        mass_components=mass_components,
        uncertainty_sources=sources,
        combination_method=combination,
        nominal_clearance_margin_m=as_optional_non_negative_float(
            un_root.get('nominal_clearance_margin_m', None),
            'geometry_uncertainty_budget.nominal_clearance_margin_m',
        ),
        arm_coupling=arm,
        stow=stow,
        requirements_path=req_path,
        evidence_path=ev_path,
        uncertainty_path=un_path,
        stow_path=st_path,
        raw={
            'requirements': req_root,
            'evidence': ev_root,
            'uncertainty': un_root,
            'stow': st_root,
        },
    )


def _parse_requirements(items: list[Any]) -> tuple[RequirementRecord, ...]:
    parsed: list[RequirementRecord] = []
    for index, item in enumerate(items):
        path = f'system_requirements.requirements[{index}]'
        mapping = as_mapping(item, path)
        reject_unknown_keys(mapping, _REQ_KEYS, path)
        req_id = as_nonempty_id(
            require_key(mapping, 'requirement_id', path),
            f'{path}.requirement_id',
        )
        kind = as_allowed_str(
            require_key(mapping, 'kind', path),
            f'{path}.kind',
            ALLOWED_REQUIREMENT_KINDS,
        )
        threshold = as_optional_float(
            mapping.get('threshold', None), f'{path}.threshold'
        )
        value = as_optional_float(mapping.get('value', None), f'{path}.value')
        range_lower = as_optional_float(
            mapping.get('range_lower', None), f'{path}.range_lower'
        )
        range_upper = as_optional_float(
            mapping.get('range_upper', None), f'{path}.range_upper'
        )
        require_interval(
            range_lower, range_upper, f'{path}.range_lower', f'{path}.range_upper'
        )
        unit = as_optional_nonempty_str(mapping.get('unit', None), f'{path}.unit')
        require_unit_when_numeric(
            any(item is not None for item in (threshold, value, range_lower, range_upper)),
            unit,
            f'{path}.unit',
        )
        status = _requirement_status(
            kind, threshold, value, range_lower, range_upper
        )
        parsed.append(
            RequirementRecord(
                requirement_id=req_id,
                title=as_str(require_key(mapping, 'title', path), f'{path}.title'),
                category=as_allowed_str(
                    require_key(mapping, 'category', path),
                    f'{path}.category',
                    ALLOWED_CATEGORIES,
                ),
                description=as_str(
                    require_key(mapping, 'description', path),
                    f'{path}.description',
                ),
                rationale=as_str(
                    require_key(mapping, 'rationale', path),
                    f'{path}.rationale',
                ),
                verification_method=as_allowed_str(
                    require_key(mapping, 'verification_method', path),
                    f'{path}.verification_method',
                    ALLOWED_VERIFICATION_METHODS,
                ),
                required_evidence_ids=as_id_list(
                    require_key(mapping, 'required_evidence_ids', path),
                    f'{path}.required_evidence_ids',
                ),
                linked_test_ids=as_id_list(
                    require_key(mapping, 'linked_test_ids', path),
                    f'{path}.linked_test_ids',
                ),
                linked_report_fields=as_id_list(
                    require_key(mapping, 'linked_report_fields', path),
                    f'{path}.linked_report_fields',
                ),
                threshold=threshold,
                value=value,
                range_lower=range_lower,
                range_upper=range_upper,
                unit=unit,
                applicability=as_str(
                    require_key(mapping, 'applicability', path),
                    f'{path}.applicability',
                ),
                blocking=as_bool(
                    require_key(mapping, 'blocking', path), f'{path}.blocking'
                ),
                notes=as_str(require_key(mapping, 'notes', path), f'{path}.notes'),
                kind=kind,
                status=status,
            )
        )
    require_unique_ids(
        (item.requirement_id for item in parsed), 'requirement'
    )
    return tuple(parsed)


def _requirement_status(
    kind: str,
    threshold: float | None,
    value: float | None,
    range_lower: float | None,
    range_upper: float | None,
) -> str:
    if kind != KIND_QUANTITATIVE:
        return REQUIREMENT_SPECIFIED
    if all(item is None for item in (threshold, value, range_lower, range_upper)):
        return REQUIREMENT_INCOMPLETE
    return REQUIREMENT_SPECIFIED


def _parse_tests(items: list[Any]) -> tuple[TestRecord, ...]:
    parsed: list[TestRecord] = []
    for index, item in enumerate(items):
        path = f'system_requirements.tests[{index}]'
        mapping = as_mapping(item, path)
        reject_unknown_keys(mapping, _TEST_KEYS, path)
        status = as_str(require_key(mapping, 'status', path), f'{path}.status')
        if status != TEST_NOT_PERFORMED:
            raise InvalidInputError(
                f'{path}.status must be {TEST_NOT_PERFORMED}, got {status!r}'
            )
        parsed.append(
            TestRecord(
                test_id=as_nonempty_id(
                    require_key(mapping, 'test_id', path), f'{path}.test_id'
                ),
                title=as_str(require_key(mapping, 'title', path), f'{path}.title'),
                method=as_str(
                    require_key(mapping, 'method', path), f'{path}.method'
                ),
                linked_requirement_ids=as_id_list(
                    require_key(mapping, 'linked_requirement_ids', path),
                    f'{path}.linked_requirement_ids',
                ),
                status=status,
                notes=as_str(require_key(mapping, 'notes', path), f'{path}.notes'),
            )
        )
    require_unique_ids((item.test_id for item in parsed), 'test')
    return tuple(parsed)


def _parse_evidence(items: list[Any]) -> tuple[EvidenceRecord, ...]:
    parsed: list[EvidenceRecord] = []
    for index, item in enumerate(items):
        path = f'evidence_ledger.evidence[{index}]'
        mapping = as_mapping(item, path)
        reject_unknown_keys(mapping, _EVIDENCE_KEYS, path)
        level = as_allowed_str(
            require_key(mapping, 'evidence_level', path),
            f'{path}.evidence_level',
            ALLOWED_EVIDENCE_LEVELS,
        )
        declared_status = as_optional_str(
            mapping.get('status', None), f'{path}.status'
        )
        if declared_status is not None and declared_status != level:
            raise InvalidInputError(
                f'{path}.status must match evidence_level {level!r}, '
                f'got {declared_status!r}'
            )
        record = EvidenceRecord(
            evidence_id=as_nonempty_id(
                require_key(mapping, 'evidence_id', path),
                f'{path}.evidence_id',
            ),
            component_id=as_allowed_str(
                require_key(mapping, 'component_id', path),
                f'{path}.component_id',
                ALLOWED_COMPONENT_IDS,
            ),
            parameter=as_str(
                require_key(mapping, 'parameter', path), f'{path}.parameter'
            ),
            evidence_level=level,
            value=as_optional_float(mapping.get('value', None), f'{path}.value'),
            lower=as_optional_float(mapping.get('lower', None), f'{path}.lower'),
            upper=as_optional_float(mapping.get('upper', None), f'{path}.upper'),
            unit=as_optional_nonempty_str(mapping.get('unit', None), f'{path}.unit'),
            source=as_optional_nonempty_str(
                mapping.get('source', None), f'{path}.source'
            ),
            source_date=as_optional_nonempty_str(
                mapping.get('source_date', None), f'{path}.source_date'
            ),
            measurement_method=as_optional_nonempty_str(
                mapping.get('measurement_method', None),
                f'{path}.measurement_method',
            ),
            sample_count=as_optional_int(
                mapping.get('sample_count', None), f'{path}.sample_count'
            ),
            uncertainty=as_optional_non_negative_float(
                mapping.get('uncertainty', None), f'{path}.uncertainty'
            ),
            linked_requirement_ids=as_id_list(
                require_key(mapping, 'linked_requirement_ids', path),
                f'{path}.linked_requirement_ids',
            ),
            status=level,
            notes=as_str(require_key(mapping, 'notes', path), f'{path}.notes'),
            vendor=as_optional_nonempty_str(
                mapping.get('vendor', None), f'{path}.vendor'
            ),
            model=as_optional_nonempty_str(
                mapping.get('model', None), f'{path}.model'
            ),
            access_date=as_optional_nonempty_str(
                mapping.get('access_date', None), f'{path}.access_date'
            ),
            measurement_equipment=as_optional_nonempty_str(
                mapping.get('measurement_equipment', None),
                f'{path}.measurement_equipment',
            ),
            measurement_time=as_optional_nonempty_str(
                mapping.get('measurement_time', None),
                f'{path}.measurement_time',
            ),
            test_id=as_optional_nonempty_str(
                mapping.get('test_id', None), f'{path}.test_id'
            ),
            test_conditions=as_optional_nonempty_str(
                mapping.get('test_conditions', None), f'{path}.test_conditions'
            ),
            raw_result=as_optional_nonempty_str(
                mapping.get('raw_result', None), f'{path}.raw_result'
            ),
            verdict=as_optional_nonempty_str(
                mapping.get('verdict', None), f'{path}.verdict'
            ),
            uncertainty_unit=as_optional_nonempty_str(
                mapping.get('uncertainty_unit', None),
                f'{path}.uncertainty_unit',
            ),
        )
        require_unit_when_numeric(
            any(
                item is not None
                for item in (record.value, record.lower, record.upper)
            ),
            record.unit,
            f'{path}.unit',
        )
        validate_evidence_level_metadata(record, path)
        parsed.append(record)
    require_unique_ids((item.evidence_id for item in parsed), 'evidence')
    return tuple(parsed)


def _parse_mass_components(items: list[Any]) -> tuple[MassComponent, ...]:
    parsed: list[MassComponent] = []
    for index, item in enumerate(items):
        path = f'evidence_ledger.mass_components[{index}]'
        mapping = as_mapping(item, path)
        reject_unknown_keys(mapping, _MASS_KEYS, path)
        lower = as_optional_non_negative_float(
            mapping.get('mass_lower_kg', None), f'{path}.mass_lower_kg'
        )
        upper = as_optional_non_negative_float(
            mapping.get('mass_upper_kg', None), f'{path}.mass_upper_kg'
        )
        require_interval(
            lower, upper, f'{path}.mass_lower_kg', f'{path}.mass_upper_kg'
        )
        parsed.append(
            MassComponent(
                component_id=as_nonempty_id(
                    require_key(mapping, 'component_id', path),
                    f'{path}.component_id',
                ),
                quantity=as_positive_int(
                    require_key(mapping, 'quantity', path), f'{path}.quantity'
                ),
                mass_lower_kg=lower,
                mass_upper_kg=upper,
                evidence_id=as_str(
                    require_key(mapping, 'evidence_id', path),
                    f'{path}.evidence_id',
                ).strip(),
                evidence_level=EVIDENCE_MISSING,
                completeness_status=COMPONENT_INCOMPLETE,
                notes=as_str(require_key(mapping, 'notes', path), f'{path}.notes'),
            )
        )
    require_unique_ids((item.component_id for item in parsed), 'component')
    ids = {item.component_id for item in parsed}
    missing = [item for item in REQUIRED_MASS_LEDGER_ITEMS if item not in ids]
    extra = sorted(ids - set(REQUIRED_MASS_LEDGER_ITEMS))
    if missing:
        raise InvalidInputError(
            f'evidence_ledger.mass_components missing required G2 items: {missing}'
        )
    if extra:
        raise InvalidInputError(
            f'evidence_ledger.mass_components unknown items: {extra}'
        )
    return tuple(parsed)


def _parse_uncertainty_sources(
    items: list[Any],
) -> tuple[UncertaintySource, ...]:
    parsed: list[UncertaintySource] = []
    for index, item in enumerate(items):
        path = f'geometry_uncertainty_budget.sources[{index}]'
        mapping = as_mapping(item, path)
        reject_unknown_keys(mapping, _UNCERT_KEYS, path)
        lower = as_optional_float(mapping.get('lower_m', None), f'{path}.lower_m')
        upper = as_optional_float(mapping.get('upper_m', None), f'{path}.upper_m')
        allowance = as_optional_non_negative_float(
            mapping.get('allowance_m', None), f'{path}.allowance_m'
        )
        require_interval(lower, upper, f'{path}.lower_m', f'{path}.upper_m')
        unit = as_str(require_key(mapping, 'unit', path), f'{path}.unit')
        if unit != 'm':
            raise InvalidInputError(f'{path}.unit must be m, got {unit!r}')
        parsed.append(
            UncertaintySource(
                source_id=as_nonempty_id(
                    require_key(mapping, 'source_id', path), f'{path}.source_id'
                ),
                lower_m=lower,
                upper_m=upper,
                allowance_m=allowance,
                unit=unit,
                evidence_id=as_str(
                    require_key(mapping, 'evidence_id', path),
                    f'{path}.evidence_id',
                ).strip(),
                notes=as_str(require_key(mapping, 'notes', path), f'{path}.notes'),
            )
        )
    require_unique_ids((item.source_id for item in parsed), 'uncertainty source')
    ids = {item.source_id for item in parsed}
    missing = [item for item in REQUIRED_UNCERTAINTY_SOURCES if item not in ids]
    extra = sorted(ids - set(REQUIRED_UNCERTAINTY_SOURCES))
    if missing:
        raise InvalidInputError(
            f'geometry_uncertainty_budget.sources missing: {missing}'
        )
    if extra:
        raise InvalidInputError(
            f'geometry_uncertainty_budget.sources unknown: {extra}'
        )
    return tuple(parsed)


def _parse_arm_coupling(raw: Mapping[str, Any]) -> ArmCouplingContract:
    path = 'geometry_uncertainty_budget.arm_radius_mass_coupling'
    reject_unknown_keys(raw, _ARM_KEYS, path)
    lower_lin = as_optional_non_negative_float(
        raw.get('linear_mass_lower_kg_per_m', None),
        f'{path}.linear_mass_lower_kg_per_m',
    )
    upper_lin = as_optional_non_negative_float(
        raw.get('linear_mass_upper_kg_per_m', None),
        f'{path}.linear_mass_upper_kg_per_m',
    )
    require_interval(
        lower_lin,
        upper_lin,
        f'{path}.linear_mass_lower_kg_per_m',
        f'{path}.linear_mass_upper_kg_per_m',
    )
    lower_con = as_optional_non_negative_float(
        raw.get('connector_mass_lower_kg', None),
        f'{path}.connector_mass_lower_kg',
    )
    upper_con = as_optional_non_negative_float(
        raw.get('connector_mass_upper_kg', None),
        f'{path}.connector_mass_upper_kg',
    )
    require_interval(
        lower_con,
        upper_con,
        f'{path}.connector_mass_lower_kg',
        f'{path}.connector_mass_upper_kg',
    )
    lower_wire = as_optional_non_negative_float(
        raw.get('wiring_mass_lower_kg_per_m', None),
        f'{path}.wiring_mass_lower_kg_per_m',
    )
    upper_wire = as_optional_non_negative_float(
        raw.get('wiring_mass_upper_kg_per_m', None),
        f'{path}.wiring_mass_upper_kg_per_m',
    )
    require_interval(
        lower_wire,
        upper_wire,
        f'{path}.wiring_mass_lower_kg_per_m',
        f'{path}.wiring_mass_upper_kg_per_m',
    )
    lower_reinf = as_optional_non_negative_float(
        raw.get('reinforcement_mass_lower_kg', None),
        f'{path}.reinforcement_mass_lower_kg',
    )
    upper_reinf = as_optional_non_negative_float(
        raw.get('reinforcement_mass_upper_kg', None),
        f'{path}.reinforcement_mass_upper_kg',
    )
    require_interval(
        lower_reinf,
        upper_reinf,
        f'{path}.reinforcement_mass_lower_kg',
        f'{path}.reinforcement_mass_upper_kg',
    )
    return ArmCouplingContract(
        baseline_radius_m=as_optional_non_negative_float(
            raw.get('baseline_radius_m', None), f'{path}.baseline_radius_m'
        ),
        candidate_radius_m=as_optional_non_negative_float(
            raw.get('candidate_radius_m', None), f'{path}.candidate_radius_m'
        ),
        extension_length_per_arm_m=as_optional_non_negative_float(
            raw.get('extension_length_per_arm_m', None),
            f'{path}.extension_length_per_arm_m',
        ),
        arm_count=_optional_positive_int(
            raw.get('arm_count', None), f'{path}.arm_count'
        ),
        linear_mass_lower_kg_per_m=lower_lin,
        linear_mass_upper_kg_per_m=upper_lin,
        connector_mass_lower_kg=lower_con,
        connector_mass_upper_kg=upper_con,
        wiring_mass_lower_kg_per_m=lower_wire,
        wiring_mass_upper_kg_per_m=upper_wire,
        reinforcement_mass_lower_kg=lower_reinf,
        reinforcement_mass_upper_kg=upper_reinf,
        evidence_ids=as_id_list(
            require_key(raw, 'evidence_ids', path), f'{path}.evidence_ids'
        ),
        notes=as_str(require_key(raw, 'notes', path), f'{path}.notes'),
    )


def _optional_positive_int(value: Any, path: str) -> int | None:
    number = as_optional_int(value, path)
    if number is None:
        return None
    if number < 1:
        raise InvalidInputError(f'{path} must be null or >= 1, got {number}')
    return number


def _parse_stow(root: Mapping[str, Any]) -> StowContract:
    path = 'stow_requirements'
    numeric = {
        name: as_optional_non_negative_float(root.get(name, None), f'{path}.{name}')
        for name in (
            'maximum_stowed_length_m',
            'maximum_stowed_width_m',
            'maximum_stowed_height_m',
            'minimum_rotor_to_leg_clearance_m',
            'maximum_transition_time_s',
            'actuator_torque_lower_nm',
            'actuator_torque_upper_nm',
            'lock_load_capacity_n',
            'lock_stiffness_nm_per_rad',
            'position_repeatability_rad',
        )
    }
    require_interval(
        numeric['actuator_torque_lower_nm'],
        numeric['actuator_torque_upper_nm'],
        f'{path}.actuator_torque_lower_nm',
        f'{path}.actuator_torque_upper_nm',
    )
    return StowContract(
        maximum_stowed_length_m=numeric['maximum_stowed_length_m'],
        maximum_stowed_width_m=numeric['maximum_stowed_width_m'],
        maximum_stowed_height_m=numeric['maximum_stowed_height_m'],
        minimum_rotor_to_leg_clearance_m=numeric[
            'minimum_rotor_to_leg_clearance_m'
        ],
        maximum_transition_time_s=numeric['maximum_transition_time_s'],
        actuator_torque_lower_nm=numeric['actuator_torque_lower_nm'],
        actuator_torque_upper_nm=numeric['actuator_torque_upper_nm'],
        lock_load_capacity_n=numeric['lock_load_capacity_n'],
        lock_stiffness_nm_per_rad=numeric['lock_stiffness_nm_per_rad'],
        position_repeatability_rad=numeric['position_repeatability_rad'],
        power_loss_safe_state=as_optional_nonempty_str(
            root.get('power_loss_safe_state', None),
            f'{path}.power_loss_safe_state',
        ),
        landing_deployment_condition=as_optional_nonempty_str(
            root.get('landing_deployment_condition', None),
            f'{path}.landing_deployment_condition',
        ),
        flight_lock_verification_method=as_optional_nonempty_str(
            root.get('flight_lock_verification_method', None),
            f'{path}.flight_lock_verification_method',
        ),
        emergency_recovery_requirement=as_optional_nonempty_str(
            root.get('emergency_recovery_requirement', None),
            f'{path}.emergency_recovery_requirement',
        ),
        notes=as_str(require_key(root, 'notes', path), f'{path}.notes'),
    )


def _cross_check_ids(
    requirements: tuple[RequirementRecord, ...],
    tests: tuple[TestRecord, ...],
    evidence: tuple[EvidenceRecord, ...],
    mass_components: tuple[MassComponent, ...],
    sources: tuple[UncertaintySource, ...],
    arm: ArmCouplingContract,
) -> None:
    all_ids = (
        [item.requirement_id for item in requirements]
        + [item.test_id for item in tests]
        + [item.evidence_id for item in evidence]
    )
    require_unique_ids(all_ids, 'official')
    evidence_ids = {item.evidence_id for item in evidence}
    for item in mass_components:
        if item.evidence_id not in evidence_ids:
            raise InvalidInputError(
                f'mass_components {item.component_id!r} references missing '
                f'evidence {item.evidence_id!r}'
            )
    for source in sources:
        if source.evidence_id not in evidence_ids:
            raise InvalidInputError(
                f'uncertainty source {source.source_id!r} references missing '
                f'evidence {source.evidence_id!r}'
            )
    for evidence_id in arm.evidence_ids:
        if evidence_id not in evidence_ids:
            raise InvalidInputError(
                f'arm_radius_mass_coupling references missing evidence '
                f'{evidence_id!r}'
            )
    reject_claimed_high_level_without_quantitative_content(requirements, evidence)
