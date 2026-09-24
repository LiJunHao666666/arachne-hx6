"""Geometry invariants and CLI regressions for the independent layout exercise."""

import importlib.util
import json
import math
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "hexa_layout.py"
SPEC = importlib.util.spec_from_file_location("hexa_layout", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_symmetry_and_clearance():
    result = MODULE.build_layout()
    assert len(result["pair_clearances"]) == 15
    assert result["min_rotor_clearance_m"] == pytest.approx(0.03)
    assert result["body_clearance_m"] == pytest.approx(0.04)
    for a, b in zip(result["rotors"][:3], result["rotors"][3:]):
        assert a["x_m"] == pytest.approx(-b["x_m"])
        assert a["y_m"] == pytest.approx(-b["y_m"])
        assert math.hypot(a["x_m"], a["y_m"]) == pytest.approx(0.12)
    assert result["rotors"][0]["x_m"] > 0
    assert result["rotors"][0]["y_m"] > 0


@pytest.mark.parametrize("channels", [(1, 1, 3, 4, 5, 6), (1, 2), (0, 2, 3, 4, 5, 6), (True, 2, 3, 4, 5, 6)])
def test_invalid_mapping(channels):
    with pytest.raises(ValueError):
        MODULE.build_layout(channels=channels)


def test_mapping_does_not_move_geometry():
    a = MODULE.build_layout()
    b = MODULE.build_layout(channels=(6, 5, 4, 3, 2, 1))
    assert [r["channel"] for r in b["rotors"]] == [6, 5, 4, 3, 2, 1]
    for x, y in zip(a["rotors"], b["rotors"]):
        assert (x["slot"], x["x_m"], x["y_m"]) == (y["slot"], y["x_m"], y["y_m"])


@pytest.mark.parametrize("value", [0, -1, float("nan"), float("inf"), True, 11])
@pytest.mark.parametrize("field", ["arm_m", "prop_radius_m", "body_radius_m"])
def test_invalid_dimensions(field, value):
    with pytest.raises(ValueError):
        MODULE.build_layout(**{field: value})


@pytest.mark.parametrize("kwargs", [{"prop_radius_m": 0.06}, {"body_radius_m": 0.08}])
def test_touching_or_overlapping_fails(kwargs):
    assert MODULE.build_layout(**kwargs)["planar_clearance"] == "FAIL"


def test_cli_artifacts_and_failure_status(tmp_path):
    for arm, expected in [("0.12", 0), ("0.08", 1)]:
        result = subprocess.run([sys.executable, str(SCRIPT), "--arm-m", arm,
                                 "--output-dir", str(tmp_path)], capture_output=True, text=True)
        assert result.returncode == expected, result.stderr
        data = json.loads((tmp_path / "layout.json").read_text())
        assert data["procurement_allowed"] is False
        assert data["flight_readiness"] == "UNDETERMINED"
        ET.parse(tmp_path / "layout.svg")
    result = subprocess.run([sys.executable, str(SCRIPT), "--arm-m", "nan",
                             "--output-dir", str(tmp_path / "invalid")], capture_output=True)
    assert result.returncode == 2
    assert not (tmp_path / "invalid").exists()
