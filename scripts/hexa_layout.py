"""Independent offline geometry exercise; no hardware or flight claims."""

import argparse
import json
import math
from pathlib import Path


def build_layout(arm_m=0.12, prop_radius_m=0.045, body_radius_m=0.035,
                 channels=(1, 2, 3, 4, 5, 6)):
    """Build a planar six-slot layout with explicit simulated channel mapping."""
    for name, value in (("arm_m", arm_m), ("prop_radius_m", prop_radius_m),
                        ("body_radius_m", body_radius_m)):
        if (isinstance(value, bool) or not isinstance(value, (int, float))
                or not math.isfinite(value) or not 0.001 <= value <= 10):
            raise ValueError(f"{name} must be finite and between 0.001 and 10 m")
    channels = tuple(channels)
    if (len(channels) != 6 or any(type(c) is not int for c in channels)
            or set(channels) != set(range(1, 7))):
        raise ValueError("channels must be a permutation of integers 1..6")
    rotors = []
    for i, channel in enumerate(channels):
        theta = math.radians(30 + 60 * i)
        rotors.append(dict(slot=f"R{i + 1}", channel=channel,
                           x_m=arm_m * math.cos(theta),
                           y_m=arm_m * math.sin(theta), z_m=0.0,
                           rotation="CCW" if i % 2 == 0 else "CW"))
    gaps = []
    for i, a in enumerate(rotors):
        for b in rotors[i + 1:]:
            distance = math.hypot(a["x_m"] - b["x_m"], a["y_m"] - b["y_m"])
            gaps.append(dict(slots=[a["slot"], b["slot"]],
                             clearance_m=distance - 2 * prop_radius_m))
    body_gap = arm_m - body_radius_m - prop_radius_m
    minimum = min(g["clearance_m"] for g in gaps)
    return dict(schema_version=1, status="ANALYSIS_ONLY",
                procurement_allowed=False, flight_readiness="UNDETERMINED",
                parameter_evidence="PLANNING_ASSUMPTION",
                frame="x forward, y left, z up; viewed from above",
                arm_m=arm_m, prop_radius_m=prop_radius_m,
                body_radius_m=body_radius_m, rotors=rotors,
                pair_clearances=gaps, body_clearance_m=body_gap,
                min_rotor_clearance_m=minimum,
                planar_clearance="PASS" if min(body_gap, minimum) > 1e-9 else "FAIL",
                limitations=["No flight dynamics or structural validation",
                             "Circles are planar placeholders; no arm/body thickness",
                             "Channels and rotation are not firmware wiring instructions"])


def to_svg(layout):
    """Draw front-up, left-left geometry with a common scale across the drawing."""
    extent = max(layout["arm_m"] + layout["prop_radius_m"], layout["body_radius_m"])
    scale = 200 / extent
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 620">',
             '<rect width="600" height="620" fill="white"/>',
             '<g font-family="sans-serif" fill="#172033">',
             '<text x="20" y="28">HEXA layout - ANALYSIS_ONLY - NOT FOR PROCUREMENT</text>',
             '<text x="20" y="52">Planning dimensions; no flight validation</text>',
             '<text x="260" y="82">FRONT +x</text>',
             '<text x="15" y="315">LEFT +y</text>']
    radius = layout["prop_radius_m"] * scale
    for r in layout["rotors"]:
        x, y = 300 - r["y_m"] * scale, 310 - r["x_m"] * scale
        parts.append(f'<line x1="300" y1="310" x2="{x}" y2="{y}" stroke="#536579" stroke-width="5"/>')
        parts.append(f'<circle cx="{x}" cy="{y}" r="{radius}" fill="#cce5ff" fill-opacity="0.6" stroke="#245d96"/>')
        parts.append(f'<text x="{x}" y="{y}" text-anchor="middle" font-size="12">{r["slot"]} / CH{r["channel"]}</text>')
        parts.append(f'<text x="{x}" y="{y + 15}" text-anchor="middle" font-size="12">{r["rotation"]}</text>')
    parts.append(f'<circle cx="300" cy="310" r="{layout["body_radius_m"] * scale}" fill="#536579"/>')
    for i, label in enumerate((f'Arm: {layout["arm_m"]:.3f} m; prop radius: {layout["prop_radius_m"]:.3f} m',
                               f'Planar clearance: {layout["planar_clearance"]}',
                               'CW/CCW viewed from above; simulated channel numbers')):
        parts.append(f'<text x="20" y="{555 + 24 * i}" font-size="14">{label}</text>')
    return "\n".join(parts + ['</g></svg>'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arm-m", type=float, default=0.12)
    parser.add_argument("--prop-radius-m", type=float, default=0.045)
    parser.add_argument("--body-radius-m", type=float, default=0.035)
    parser.add_argument("--channels", type=int, nargs=6, default=[1, 2, 3, 4, 5, 6])
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        layout = build_layout(args.arm_m, args.prop_radius_m, args.body_radius_m, args.channels)
    except ValueError as exc:
        parser.error(str(exc))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "layout.json").write_text(json.dumps(layout, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    (args.output_dir / "layout.svg").write_text(to_svg(layout), encoding="utf-8")
    print(f'Planar clearance: {layout["planar_clearance"]}; flight: UNDETERMINED')
    print(args.output_dir.resolve())
    return 0 if layout["planar_clearance"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
