# Arachne HX6 whole-system module study

State: `ANALYSIS_ONLY`; `procurement_allowed=false`. Open
`system_module_study.kicad_sch` in KiCad's schematic editor. The A3 sheet is
an editable **functional architecture** for the first flying hexarotor
milestone. ERC passes with zero violations; that means only that the drawn
logical nets are internally connected as intended.

- BT1: candidate battery pack, with capacity, cell count, connector and
  protection still unknown.
- J1: **off-board** flight-controller module. Its twelve symbol pins are
  internal study numbering; they are not a manufacturer pinout.
- J2: receiver module with conceptual data, ground and supply connections.
- J3–J8: six ESC *channels*, which do not imply six separate purchasable ESC
  modules. Each channel symbol separates signal, signal ground, battery power,
  and three motor phases. Pin 8 is reserved with a no-connect marker.
- J9–J14: six conceptual three-phase brushless motors. Their physical model,
  phase order, propeller and rotation assignment remain unknown.
- J15: **conceptual** power distribution / flight-controller supply boundary.
  Battery input, ESC power bus, and FC supply use separate named nets. This
  symbol is not an electrical circuit and does not represent a selected BEC.
  `SYSTEM_RETURN_TBD` shows that control signals need a common reference;
  the actual return wiring, protection and current paths require design.

The sheet does **not** specify a PCB or custom flight controller. No symbol
has an approved physical footprint or part number. The architecture omits
required real-world details including power distribution, wire gauge, fuse or
protection scheme, switch, charger, radio transmitter, frame, mounting,
propellers, mass/thrust evidence, and safe firmware configuration. The
`RX_SUPPLY_TBD`, battery, ESC-bus and FC-supply labels are placeholders, not
permission to connect a battery directly to any unselected device. Never wire or fabricate
from this sheet.

The project screening file currently refers to a SpeedyBee F405 V4, whereas
the separate `fc_breakout_study` examines F405 V5 interface markings. These
are **two references**, not one approved component. Do not merge their pad
names, dimensions, mass or output mapping. The hardware gate currently reports
compatibility, cost and physics as `UNDETERMINED`; its 299 CNY known subtotal
includes a historical FC listing and a 60 CNY reserve, not a verified shopping
cart. The remaining 301 CNY is an upper bound for unknown rows, not money
available after actual purchases.

Next: keep the simulation model as the control baseline; choose exact real
modules only after the project hardware gate closes compatibility, delivered
cost, and measured thrust/mass evidence. Then obtain each manufacturer's
pinout and ratings, revise this sheet, and only later derive a specific PCB.
