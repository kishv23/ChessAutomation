"""Arm drivers.

SimulatedArm  records every command and tracks the fingertip; used in tests and
              for dry runs before a real game.
SerialArm     talks to a microcontroller (Arduino or ESP32 running servo
              firmware) over USB serial with a small line protocol:

                J <base> <shoulder> <elbow> <wrist>   joint targets in degrees
                G <0|1>                               gripper open / closed
                H                                     home
              Each command is answered with "ok" or "err <message>".
"""
from __future__ import annotations

import math
import time
from typing import List, Optional, Protocol, Tuple

from robot.kinematics import ArmSpec, Joints, forward


class ArmError(RuntimeError):
    pass


class ArmDriver(Protocol):
    def move_joints(self, joints: Joints) -> None: ...
    def grip(self, closed: bool) -> None: ...
    def home(self) -> None: ...


class SimulatedArm:
    def __init__(self, spec: ArmSpec = ArmSpec()):
        self.spec = spec
        self.log: List[Tuple[str, object]] = []
        self.joints: Optional[Joints] = None
        self.gripping = False

    def move_joints(self, joints: Joints) -> None:
        self.joints = joints
        self.log.append(("move", joints))

    def grip(self, closed: bool) -> None:
        self.gripping = closed
        self.log.append(("grip", closed))

    def home(self) -> None:
        self.joints = None
        self.gripping = False
        self.log.append(("home", None))

    @property
    def tip(self) -> Optional[Tuple[float, float, float]]:
        return forward(self.spec, self.joints) if self.joints else None


class SerialArm:
    def __init__(self, port: str, baud: int = 115200, timeout: float = 5.0, settle: float = 2.0, conn=None):
        if conn is None:
            import serial  # pyserial; optional so the simulator runs without it

            conn = serial.Serial(port, baud, timeout=timeout)
            time.sleep(settle)  # most boards reset when the port opens
        self.conn = conn

    def _send(self, line: str) -> None:
        self.conn.write((line + "\n").encode("ascii"))
        reply = self.conn.readline().decode("ascii", "replace").strip()
        if reply != "ok":
            raise ArmError(f"arm rejected {line!r}: {reply or 'no reply (timeout)'}")

    def move_joints(self, joints: Joints) -> None:
        deg = [math.degrees(a) for a in joints.as_tuple()]
        self._send("J " + " ".join(f"{d:.2f}" for d in deg))

    def grip(self, closed: bool) -> None:
        self._send(f"G {1 if closed else 0}")

    def home(self) -> None:
        self._send("H")

    def close(self) -> None:
        self.conn.close()
