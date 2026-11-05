"""Inverse kinematics for a 4-DOF desktop arm with a vertical gripper.

Joints: base yaw, shoulder pitch, elbow pitch, wrist pitch. The wrist is
always set so the gripper points straight down, which is what picking chess
pieces needs and reduces the problem to a planar two-link solve.

All angles are radians. Zero shoulder points the upper arm horizontally
forward; positive pitch lifts it.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Tuple


class Unreachable(ValueError):
    pass


@dataclass(frozen=True)
class ArmSpec:
    base_height: float = 95.0     # shoulder axis above the table (mm)
    upper_arm: float = 180.0      # shoulder -> elbow
    forearm: float = 180.0        # elbow -> wrist
    gripper: float = 75.0         # wrist -> fingertip, pointing down
    limits: Tuple[Tuple[float, float], ...] = (
        (-math.pi, math.pi),
        (-math.radians(10), math.radians(170)),
        (-math.radians(160), math.radians(10)),
        (-math.radians(200), math.radians(20)),
    )


@dataclass(frozen=True)
class Joints:
    base: float
    shoulder: float
    elbow: float
    wrist: float

    def as_tuple(self) -> Tuple[float, float, float, float]:
        return (self.base, self.shoulder, self.elbow, self.wrist)

    def degrees(self) -> Dict[str, float]:
        return {k: round(math.degrees(v), 2) for k, v in zip(("base", "shoulder", "elbow", "wrist"), self.as_tuple())}


def inverse(spec: ArmSpec, x: float, y: float, z: float) -> Joints:
    """Joint angles that put the fingertip at (x, y, z) with the gripper vertical."""
    base = math.atan2(y, x)
    r = math.hypot(x, y)
    # Wrist centre sits directly above the fingertip.
    wz = z + spec.gripper - spec.base_height
    d2 = r * r + wz * wz
    l1, l2 = spec.upper_arm, spec.forearm
    cos_elbow = (d2 - l1 * l1 - l2 * l2) / (2 * l1 * l2)
    if not -1.0 <= cos_elbow <= 1.0:
        raise Unreachable(f"({x:.0f}, {y:.0f}, {z:.0f}) is {'out of' if cos_elbow > 1 else 'inside minimum'} reach")
    elbow = -math.acos(cos_elbow)  # elbow-up configuration
    shoulder = math.atan2(wz, r) - math.atan2(l2 * math.sin(elbow), l1 + l2 * math.cos(elbow))
    wrist = -math.pi / 2 - shoulder - elbow  # keep the gripper pointing straight down
    joints = Joints(base, shoulder, elbow, wrist)
    check_limits(spec, joints)
    return joints


def forward(spec: ArmSpec, j: Joints) -> Tuple[float, float, float]:
    """Fingertip position for joint angles; used to verify IK and in the simulator."""
    a1 = j.shoulder
    a2 = j.shoulder + j.elbow
    a3 = a2 + j.wrist
    r = spec.upper_arm * math.cos(a1) + spec.forearm * math.cos(a2) + spec.gripper * math.cos(a3)
    z = spec.base_height + spec.upper_arm * math.sin(a1) + spec.forearm * math.sin(a2) + spec.gripper * math.sin(a3)
    return r * math.cos(j.base), r * math.sin(j.base), z


def check_limits(spec: ArmSpec, j: Joints) -> None:
    for name, value, (lo, hi) in zip(("base", "shoulder", "elbow", "wrist"), j.as_tuple(), spec.limits):
        if not lo - 1e-9 <= value <= hi + 1e-9:
            raise Unreachable(f"{name} angle {math.degrees(value):.1f} deg is outside [{math.degrees(lo):.0f}, {math.degrees(hi):.0f}]")
