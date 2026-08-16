# G3 Requirements, Evidence Ledger, and Uncertainty Gates

**ANALYSIS_ONLY**
**NOT_FOR_PROCUREMENT**
**overall_system_readiness: UNDETERMINED**
**procurement_allowed: false**

This document is the G3 engineering contract for Arachne-HX6. It is not a
buy list, flyable claim, hardware-validation record, or authorization to
enter the next stage.

## Scope

G3 establishes:

- a system requirements contract
- an evidence ledger
- a mass-interval budget over the G2 19-item ledger
- a geometry uncertainty budget
- a stow-requirements contract
- an arm-radius / mass coupling contract
- bidirectional requirement-evidence-test-report traceability
- fail-closed readiness gates
- JSON / CSV / Markdown reports and the `requirements_report` CLI

G3 does not modify merged G1 identifiers, joints, or topology, and does
not change the G1 URDF / Xacro implementation.

## Safety and procurement boundary

Arachne-HX6 is simulation-first and non-weaponized. Official work is limited
to disaster response, environmental sensing, hazardous-area inspection, and
non-weaponized reconnaissance / remote inspection.

Completing G3 does **not** automatically allow procurement, physical
assembly, or the next stage. Procurement status may change only after:

- safety requirements are met
- mass / evidence ledgers are complete
- risk assessment is complete
- site rules are defined and accepted
- formal approval is recorded
- an independent official gate explicitly authorizes the change

Until that independent gate exists, `procurement_allowed` remains `false`.

This contract does not design or compute real launch, self-propulsion,
explosive, penetrative, destructive, ballistic, automatic-attack, or
weaponized control chains. Vision or perception outputs must not connect
directly to any hazardous action. Side pods remain fixed, non-launching
sensor placeholders.

If a physical concept demonstration is ever discussed, the article must
remain constrained by enclosed rails, tethers, or mechanical stops for the
entire demonstration. It must not free-fly or self-propel. Speed, kinetic
energy, materials, pinch distances, and stopping distance must be safety
assessed. Guards, e-stop, and human control are required. No such
demonstration is authorized by G3.

## Fail-closed evidence sufficiency

`SPECIFIED` means the clause is written. It is not verification and not
satisfaction.

Evidence is sufficient only when every required evidence item is
`VENDOR_DECLARED`, `MEASURED`, or `TEST_VALIDATED`.

The following are **not** sufficient:

- no required evidence IDs
- every required item is `MISSING`
- every required item is `PLANNING_ASSUMPTION`
- a mixed set that still contains `MISSING` and/or `PLANNING_ASSUMPTION`
- any other level outside the hardware-sufficient set

`PLANNING_ASSUMPTION` cannot increase `requirements_verified` or
`requirements_satisfied`.

Official sets are computed, not hardcoded:

- `missing_evidence_requirement_ids`
- `planning_assumption_only_requirement_ids`
- `mixed_insufficient_evidence_requirement_ids`
- `sufficient_evidence_requirement_ids`
- `evidence_blocked_requirement_ids`
- `incomplete_blocking_requirement_ids`
- `all_blocking_requirement_ids` = sorted unique union of
  `incomplete_blocking_requirement_ids` and
  `evidence_blocked_requirement_ids`
- `nonblocking_unverified_requirement_ids`
- `unsatisfied_blocking_requirement_ids`
- `blocking_reason_codes`

Every `blocking=true` requirement that is not satisfied must have an
explicit blocker reason. Requirements excluded from `all_blocking` must
have `blocking=false`, or they must already have sufficient evidence.

Requirement-evidence and requirement-test links are bidirectional. Each
`required_evidence_ids` entry must appear in that evidence record's
`linked_requirement_ids`, and each reverse link must appear in the
requirement. The same rule applies to `linked_test_ids` and
`test.linked_requirement_ids`. Any one-way mismatch raises
`InvalidInputError`. Orphan evidence, orphan tests, or
`traceability_status != CONSISTENT` cannot open
`EVIDENCE_COMPLETE_FOR_NEXT_ANALYSIS`; the gate stays
`UNDETERMINED_EVIDENCE` with an explicit `orphan_*` or
`traceability_incomplete` reason.

Quantitative requirements keep `MISSING` and `PLANNING_ASSUMPTION` as
ordinary blockers. If cited evidence claims `VENDOR_DECLARED`,
`MEASURED`, or `TEST_VALIDATED`, it must have a finite `value` or a
complete finite `lower`/`upper` interval with `lower <= upper`, and a
non-empty unit. Vendor, model, date, or test-name metadata alone cannot
make a quantitative requirement `verified` or `sufficient`. That case
is rejected at post-load cross-validation. Qualitative requirements do
not require numeric content; they still use the existing evidence-level
metadata rules.

Top-level `requirement_id`, `test_id`, `evidence_id`, mass
`component_id`, and uncertainty `source_id` values must be non-empty
after stripping whitespace.

JSON, CSV, and Markdown reports are installed as one trio. A replace
failure restores the previous trio byte-for-byte, or leaves no official
report files if none existed. Staging and backup directories are
removed.

`unsatisfied_blocking_requirement_ids` is not “every blocking requirement
that is still open”. It is the computed set of requirements that are
`blocking=true`, already `verified`, and still not `satisfied`. Production
YAML currently has `requirements_verified = 0`, so this set is empty.
Those 48 still-open blocking requirements are recorded in `all_blocking`
with an explicit reason. A synthetic MEASURED ledger can fill
`unsatisfied_blocking` with `NOT_SATISFIED` while `all_blocking` stays
empty, because sufficient evidence is not satisfaction.

`SYS-STOW-011` is the canonical mixed case: `EV-PROC-012` is
`PLANNING_ASSUMPTION` and `EV-STOW-012` is `MISSING`. It is therefore
`MIXED_INSUFFICIENT_EVIDENCE` and belongs in `evidence_blocked` and
`all_blocking`.

## Official production posture

The official YAML inventory currently contains 48 requirements. Incomplete
numeric clauses remain `INCOMPLETE_REQUIREMENT`. No vendor-declared,
measured, or test-validated hardware evidence exists. Official sets are
computed from YAML at runtime, not assigned as a preset 33 or 48 in
production code. Independent audit evaluation of the official YAML:

- `requirements_total = 48`
- `requirements_specified = 23`
- `requirements_incomplete_specification = 25`
- `missing_evidence_requirement_ids = 8`
- `planning_assumption_only_requirement_ids = 14`
- `mixed_insufficient_evidence_requirement_ids = 1` (`SYS-STOW-011`)
- `sufficient_evidence_requirement_ids = 0`
- `evidence_blocked_requirement_ids = 23` (8 + 14 + 1)
- `incomplete_blocking_requirement_ids = 25`
- `all_blocking_requirement_ids = 48` (union of incomplete_blocking and
  evidence_blocked; also equal to every `blocking=true` row because the
  official YAML has zero `blocking=false` rows)
- `nonblocking_unverified_requirement_ids = 0`
- `unsatisfied_blocking_requirement_ids = 0` (verified-but-unsatisfied;
  verified is 0)
- `blocking_requirement_reasons = 48`
- `requirements_verified = 0`
- `requirements_satisfied = 0`
- `overall_system_readiness = UNDETERMINED`
- `readiness_gate = UNDETERMINED_REQUIREMENTS`
- `procurement_allowed = false`
- evidence levels: `MISSING=52`, `PLANNING_ASSUMPTION=14`,
  `VENDOR_DECLARED=0`, `MEASURED=0`, `TEST_VALIDATED=0`

Mass-ledger, geometry-uncertainty, stow-hardware, and arm-coupling values
stay null where unknown. Null is never treated as zero.

## Reports and CLI

```bash
source /opt/ros/jazzy/setup.bash
cd ~/arachne_hx6_ws
source install/setup.bash
ros2 run arachne_hx6_analysis requirements_report --output-dir /tmp/arachne_g3_report
```

Paste the commands above in the Cursor WSL Ubuntu terminal, prompt similar
to:

`lijunhao@T480sYYT:~/arachne_hx6_ws$`

JSON, CSV, and Markdown must agree on sets and counts. Forbidden official
status words remain: `VIABLE`, `FLYABLE`, `SAFE_TO_FLY`,
`PROCUREMENT_READY`, `RECOMMENDED_FOR_PURCHASE`, `VALIDATED_HARDWARE`,
`STOWED_PASS`, `VALID_STOWED_POSE`.

## G1.5 / G2 invariance

G3 must not change G1.5 or G2 mathematics or report contracts except
generation timestamps and description asset-path resolution
(`install/.../share/arachne_hx6_description` versus
`src/arachne_hx6_description`). G2 remains 30 geometry candidates, 270
joint-gate rows, 18151 certified distance solves, and 17/128 peak
evaluations, with certified error bound `<= 1e-9 m`. G2 joint-gate
totals remain 144 `REJECTED_GEOMETRY`, 61 `REJECTED_ENERGY_CLOSURE`,
and 65 `UNDETERMINED_MASS_LEDGER`.

## Test-count vocabularies

Four counting methods are distinct and must not be mixed:

1. `arachne_hx6_analysis` pytest case count: **164** collected / 164 passed
   (G1.5+G2 103 + G3 `test_requirements_evidence.py` 61)
2. `arachne_hx6_description` pytest case count: **8** collected / 8 passed
3. simple sum of those two pytest counts: **172**
4. `colcon test-result --verbose` official CTest summary: **173 tests,
   0 errors, 0 failures, 0 skipped** =
   `build/arachne_hx6_analysis/pytest.xml` 164 +
   `test_description.xunit.xml` 8 +
   description CTest wrapper `Test.xml` 1

`colcon test-result --all --verbose` lists those three XML files. Mixing
the CTest wrapper with pytest cases is what produced the earlier 112 vs
111 / 141 vs 142 conflicts.

G2 baseline reported 112 official tests. That figure is vocabulary 4:
103 analysis pytest + 8 description pytest + 1 description CTest wrapper.
The pytest-sum vocabulary for G2 is 111. G3 adds 61 pytest cases in
`test_requirements_evidence.py` only.
