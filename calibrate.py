#Author: Kishorekumar Vishwanathan
"""Calibrates the board position for the arm.

    python calibrate.py --port /dev/ttyUSB0 --out calibration.local.json
    python calibrate.py --check --cal calibration.local.json     # reach check only

Jog the gripper with commands like "x+5", "y-2", "z+10" until it is centred
over a1, type "ok", then repeat for h8. Every square, graveyard slot and
reserve slot is then checked for reachability before the file is saved.
"""
import argparse
import re

from robot.driver import SerialArm, SimulatedArm
from robot.geometry import BoardGeometry, Calibration
from robot.kinematics import ArmSpec, Unreachable, inverse

JOG = re.compile(r"^([xyz])\s*([+-]\d+(?:\.\d+)?)$")


def reach_report(cal: Calibration, spec: ArmSpec = ArmSpec()):
    g = BoardGeometry(cal)
    targets = {f"{f}{r}": g.square_xy(f"{f}{r}") for f in "abcdefgh" for r in "12345678"}
    for i in range(cal.graveyard_columns * cal.graveyard_rows):
        targets[f"graveyard W{i + 1}"] = g.next_graveyard_xy("P")
        targets[f"graveyard B{i + 1}"] = g.next_graveyard_xy("p")
    targets["overflow bin"] = cal.overflow_bin
    targets.update({f"reserve {k}": v for k, v in cal.reserve.items()})
    problems = []
    for name, (x, y) in targets.items():
        for z in (cal.board_z + min(cal.grip_heights.values()), cal.travel_z):
            try:
                inverse(spec, x, y, z)
            except Unreachable as exc:
                problems.append(f"{name} at z={z:.0f}: {exc}")
    return problems


def jog_to(arm, label, start, read=input, write=print, spec=ArmSpec()):
    x, y, z = start
    write(f"Centre the gripper over {label}. Commands: x+5, y-2, z+10, ok")
    while True:
        try:
            arm.move_joints(inverse(spec, x, y, z))
        except Unreachable as exc:
            write(f"  cannot reach ({x:.1f}, {y:.1f}, {z:.1f}): {exc}")
        cmd = read(f"  at ({x:.1f}, {y:.1f}, {z:.1f}) > ").strip().lower()
        if cmd == "ok":
            return x, y
        m = JOG.match(cmd)
        if not m:
            write("  unknown command")
            continue
        axis, delta = m.group(1), float(m.group(2))
        x, y, z = (x + delta, y, z) if axis == "x" else (x, y + delta, z) if axis == "y" else (x, y, z + delta)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--port")
    p.add_argument("--sim", action="store_true")
    p.add_argument("--cal", help="existing calibration to start from")
    p.add_argument("--out", default="calibration.local.json")
    p.add_argument("--check", action="store_true", help="only report reachability")
    args = p.parse_args()

    cal = Calibration.load(args.cal) if args.cal else Calibration()
    if not args.check:
        arm = SimulatedArm() if args.sim or not args.port else SerialArm(args.port)
        hover = cal.board_z + 40.0
        cal.a1 = jog_to(arm, "a1", (*cal.a1, hover))
        cal.h8 = jog_to(arm, "h8", (*cal.h8, hover))
        arm.home()

    problems = reach_report(cal)
    for line in problems:
        print("UNREACHABLE", line)
    if problems:
        raise SystemExit(f"{len(problems)} positions are out of reach; move the board closer to the arm.")
    print("All squares, graveyard slots and reserve slots are reachable.")
    if not args.check:
        cal.save(args.out)
        print("Saved", args.out)


if __name__ == "__main__":
    main()
