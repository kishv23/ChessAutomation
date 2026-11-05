"""Executes planned transfers on an arm driver.

Every transfer follows the same safe pattern so pieces are never dragged
through each other:

    travel height over source -> descend -> grip -> lift -> travel height over
    destination -> descend -> release -> lift
"""
from __future__ import annotations

import logging
from typing import List, Tuple

from robot.driver import ArmDriver
from robot.geometry import BoardGeometry
from robot.kinematics import ArmSpec, inverse
from robot.planner import GRAVEYARD, RESERVE, Transfer, plan_move

log = logging.getLogger(__name__)


class ArmController:
    def __init__(self, driver: ArmDriver, geometry: BoardGeometry, spec: ArmSpec = ArmSpec()):
        self.driver, self.geometry, self.spec = driver, geometry, spec

    def _xy(self, place: str, piece: str) -> Tuple[float, float]:
        if place == GRAVEYARD:
            return self.geometry.next_graveyard_xy()
        if place == RESERVE:
            return self.geometry.reserve_xy(piece)
        return self.geometry.square_xy(place)

    def _goto(self, x: float, y: float, z: float) -> None:
        self.driver.move_joints(inverse(self.spec, x, y, z))

    def waypoints(self, transfer: Transfer, src_xy, dst_xy) -> List[Tuple[str, object]]:
        travel = self.geometry.cal.travel_z
        grip_z = self.geometry.grip_z(transfer.piece)
        (sx, sy), (dx, dy) = src_xy, dst_xy
        return [
            ("grip", False),
            ("move", (sx, sy, travel)),
            ("move", (sx, sy, grip_z)),
            ("grip", True),
            ("move", (sx, sy, travel)),
            ("move", (dx, dy, travel)),
            ("move", (dx, dy, grip_z)),
            ("grip", False),
            ("move", (dx, dy, travel)),
        ]

    def execute(self, transfers: List[Transfer]) -> None:
        # Resolve and check every point before moving, so an unreachable square
        # aborts the move instead of leaving a piece in the gripper mid-air.
        plans = []
        for t in transfers:
            src = self._xy(t.src, t.piece)
            dst = self._xy(t.dst, t.piece)
            steps = self.waypoints(t, src, dst)
            for kind, arg in steps:
                if kind == "move":
                    inverse(self.spec, *arg)
            plans.append((t, steps))

        for t, steps in plans:
            log.info("%s: %s %s -> %s", t.reason, t.piece, t.src, t.dst)
            for kind, arg in steps:
                if kind == "move":
                    self._goto(*arg)
                else:
                    self.driver.grip(arg)

    def play(self, fen: str, uci: str) -> List[Transfer]:
        """Plans and physically performs `uci` from position `fen`."""
        transfers = plan_move(fen, uci)
        self.execute(transfers)
        return transfers

    def new_game(self) -> None:
        self.geometry.reset_graveyard()
        self.driver.home()
